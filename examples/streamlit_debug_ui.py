"""Streamlit 기반 data.go.kr API 디버그 카탈로그 뷰어."""
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
for module_name, module in list(sys.modules.items()):
    if module_name != "datagokr" and not module_name.startswith("datagokr."):
        continue
    module_file = getattr(module, "__file__", None)
    if module_file is not None and not Path(module_file).resolve().is_relative_to(SRC):
        del sys.modules[module_name]

try:
    import pandas as pd
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - 선택 실행 도구
    raise SystemExit('Streamlit UI를 쓰려면 `pip install -e ".[debug-ui]"`를 실행하세요.') from exc

from datagokr import DataGoKrClient
from datagokr.catalog import ApiCatalogEntry, ParamSpec, get_api_catalog
from datagokr.debug import DebugRun, jsonable, save_fixture

ENV_VAR_NAME = "DATA_GO_KR_SERVICE_KEY"
DEFAULT_TIMEOUT_SECONDS = 10.0


def main() -> None:
    st.set_page_config(page_title="datagokr API Debug", layout="wide")
    st.title("datagokr API Debug")
    st.session_state.setdefault("runs", {})

    rows = list(get_api_catalog())
    data_sources = sorted({row.data_source for row in rows})
    data_source = st.sidebar.selectbox("Data source", data_sources)
    source_rows = [row for row in rows if row.data_source == data_source]
    labels = [row.label for row in source_rows]
    selected_label = st.sidebar.selectbox("API", labels)
    selected = source_rows[labels.index(selected_label)]

    st.sidebar.caption(selected.description_lines[0])
    st.sidebar.caption(selected.description_lines[1])

    environment, api_key = _environment_and_auth_sidebar(selected)
    timeout = st.sidebar.number_input(
        "Timeout",
        min_value=1.0,
        max_value=60.0,
        value=DEFAULT_TIMEOUT_SECONDS,
        step=1.0,
        help="API 요청 timeout seconds입니다.",
    )
    fixture_base_dir = _fixture_base_dir_sidebar()

    tabs = st.tabs(
        [
            "Raw Response",
            "Pydantic Model",
            "Processed Result",
            "Validation Errors",
            "Debug Trace",
            "Fixture / Testcase",
        ]
    )

    with tabs[0]:
        _raw_response_tab(selected, api_key, timeout=float(timeout))
    with tabs[1]:
        _pydantic_model_tab(selected)
    with tabs[2]:
        _processed_result_tab(selected)
    with tabs[3]:
        _validation_errors_tab(selected)
    with tabs[4]:
        _debug_trace_tab(rows, selected, environment=environment)
    with tabs[5]:
        _fixture_tab(fixture_base_dir, selected)


def _environment_and_auth_sidebar(selected: ApiCatalogEntry) -> tuple[str, str]:
    st.sidebar.subheader("Environment")
    env_value = os.getenv(ENV_VAR_NAME, "")
    environment = st.sidebar.radio(
        "API key source",
        ["env", "manual"],
        index=0 if env_value else 1,
        format_func=lambda value: {
            "env": f"환경변수 사용 ({ENV_VAR_NAME})",
            "manual": "수동 입력",
        }[value],
    )
    if environment == "env":
        st.sidebar.caption(
            f"{ENV_VAR_NAME} 환경변수 값을 사용합니다."
            if env_value
            else f"{ENV_VAR_NAME} 환경변수가 비어 있습니다. "
            "값을 설정하거나 수동 입력으로 전환하세요."
        )
    else:
        st.sidebar.caption("사이드바에 직접 입력한 서비스키를 사용합니다.")

    st.sidebar.subheader("Auth")
    if environment == "manual":
        api_key = st.sidebar.text_input(
            selected.service_key_param,
            value="",
            type="password",
            placeholder="직접 입력",
            help=f"사용 가능한 env 이름: {', '.join(selected.service_key_env_names)}",
        )
    else:
        api_key = env_value

    if selected.service_key_url:
        st.sidebar.link_button("serviceKey 발급/확인", selected.service_key_url)

    return environment, api_key


def _raw_response_tab(selected: ApiCatalogEntry, api_key: str, *, timeout: float) -> None:
    st.subheader(selected.title)
    st.caption(f"{selected.data_source} / {selected.key} / {selected.endpoint}")

    try:
        submitted, params, request_options, missing = _request_form(selected)
    except ValueError as exc:
        st.error(str(exc))
        return

    preview: dict[str, Any] = {
        **params,
        selected.page_no_wire_param: request_options["page_no"],
        selected.num_rows_wire_param: request_options["num_of_rows"],
    }
    if selected.supports_response_type:
        preview[selected.response_type_param] = request_options["response_type"]
    st.subheader("Request params preview")
    st.json(preview)

    if not submitted:
        return
    if missing:
        st.error("필수 파라미터를 입력하세요: " + ", ".join(missing))
        return
    if not api_key:
        st.error(f"{selected.service_key_param}가 비어 있습니다. Auth 섹션을 확인하세요.")
        return

    try:
        with DataGoKrClient(api_key=api_key, timeout=timeout) as client:
            run = client.debug_fetch(
                selected.key,
                params=params,
                page_no=request_options["page_no"],
                num_of_rows=request_options["num_of_rows"],
                response_type=request_options["response_type"],
            )
    except Exception as exc:  # pragma: no cover - UI 표시
        st.error(str(exc))
        return

    _store_run(selected, run)
    if run.error:
        st.error(run.error["message"])
    st.json(jsonable(run.response))


def _request_form(
    selected: ApiCatalogEntry,
) -> tuple[bool, dict[str, Any], dict[str, Any], list[str]]:
    key_prefix = _selection_key(selected)

    with st.form(f"request-form:{key_prefix}"):
        st.subheader("Required parameters")
        if selected.required_params:
            required_values = _render_param_grid(selected.required_params, key_prefix=key_prefix)
        else:
            st.caption("이 API에는 필수 파라미터가 없습니다.")
            required_values = {}

        st.subheader("Optional parameters")
        if selected.optional_params:
            optional_values = _render_param_grid(selected.optional_params, key_prefix=key_prefix)
        else:
            st.caption("이 API에는 카탈로그에 등록된 선택 파라미터가 없습니다.")
            optional_values = {}

        page_no, num_of_rows, response_type = _render_common_options(selected, key_prefix)

        extra_text = st.text_area(
            "Extra params JSON",
            value="{}",
            height=110,
            help="카탈로그에 없는 provider 파라미터를 JSON object로 추가합니다.",
            key=f"{key_prefix}:extra",
        )
        submitted = st.form_submit_button("Run selected API")

    params = {**required_values, **optional_values, **_parse_extra_params(extra_text)}
    missing = [
        spec.name for spec in selected.required_params if not str(params.get(spec.name, "")).strip()
    ]
    return (
        submitted,
        {key: value for key, value in params.items() if str(value).strip()},
        {"page_no": page_no, "num_of_rows": num_of_rows, "response_type": response_type},
        missing,
    )


def _render_param_grid(specs: tuple[ParamSpec, ...], *, key_prefix: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index in range(0, len(specs), 2):
        columns = st.columns(2)
        for column, spec in zip(columns, specs[index : index + 2], strict=False):
            with column:
                widget_key = f"{key_prefix}:param:{spec.name}"
                values[spec.name] = _render_param_widget(spec, key=widget_key)
    return values


def _render_param_widget(spec: ParamSpec, *, key: str) -> Any:
    if spec.kind == "enum" and spec.choices:
        return st.selectbox(spec.label, spec.choices, help=spec.help or None, key=key)
    if spec.kind == "int":
        return st.number_input(
            spec.label,
            value=int(spec.default) if spec.default else 0,
            step=1,
            help=spec.help or None,
            key=key,
        )
    if spec.kind == "float":
        return st.number_input(
            spec.label,
            value=float(spec.default) if spec.default else 0.0,
            help=spec.help or None,
            key=key,
        )
    return st.text_input(
        spec.label,
        value=spec.default,
        placeholder=spec.help,
        help=spec.help or None,
        key=key,
    )


def _render_common_options(selected: ApiCatalogEntry, key_prefix: str) -> tuple[int, int, str]:
    columns = st.columns(3 if selected.supports_response_type else 2)
    with columns[0]:
        page_no = st.number_input(
            selected.page_no_wire_param,
            min_value=1,
            value=1,
            step=1,
            help="공공데이터포털 paging 파라미터입니다.",
            key=f"{key_prefix}:pageNo",
        )
    with columns[1]:
        num_of_rows = st.number_input(
            selected.num_rows_wire_param,
            min_value=1,
            value=selected.default_num_of_rows,
            step=1,
            help="한 페이지에 받을 row 수입니다.",
            key=f"{key_prefix}:numOfRows",
        )
    response_type = "json"
    if selected.supports_response_type:
        with columns[2]:
            response_type = st.selectbox(
                selected.response_type_param,
                selected.response_type_choices,
                index=0,
                help="응답 형식입니다.",
                key=f"{key_prefix}:type",
            )
    return int(page_no), int(num_of_rows), str(response_type)


def _parse_extra_params(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Extra params JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Extra params JSON must be an object")
    return {
        key: value
        for key, value in payload.items()
        if key not in {"serviceKey", "ServiceKey", "pageNo", "numOfRows", "type"}
    }


def _pydantic_model_tab(selected: ApiCatalogEntry) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 선택한 API를 실행하면 여기에서 Pydantic 모델을 확인합니다.")
        return
    if run.error:
        st.warning("실행 중 오류가 있습니다. Validation Errors 탭을 확인하세요.")
    st.json(jsonable(run.parsed))


def _processed_result_tab(selected: ApiCatalogEntry) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 API를 실행하면 처리된 row preview를 표시합니다.")
        return
    data = jsonable(run.processed)
    if isinstance(data, list) and data:
        st.dataframe(pd.json_normalize(data, sep="."), width="stretch", hide_index=True)
    else:
        st.json(data)


def _validation_errors_tab(selected: ApiCatalogEntry) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("아직 실행된 API가 없습니다.")
        return
    if not run.error:
        st.success("현재 실행 결과에서 validation error 또는 exception이 없습니다.")
        return
    st.error(run.error["message"])
    st.json(run.error)


def _debug_trace_tab(
    rows: list[ApiCatalogEntry],
    selected: ApiCatalogEntry,
    *,
    environment: str,
) -> None:
    run = _current_run(selected)

    st.subheader("Catalog")
    st.dataframe(
        pd.json_normalize([jsonable(row) for row in rows], sep="."),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Selected API")
    st.json(jsonable(selected))
    env_names = ", ".join(selected.service_key_env_names)
    st.caption(f"credential env: {env_names} (source: {environment})")

    if run is not None:
        st.subheader("Trace")
        st.write(list(run.trace))
        st.subheader("Request")
        st.json(jsonable(run.request))
        if run.catalog is not None:
            st.dataframe(
                pd.json_normalize([jsonable(run.catalog)], sep="."),
                width="stretch",
                hide_index=True,
            )


def _fixture_tab(fixture_base_dir: str, selected: ApiCatalogEntry) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 API를 실행한 뒤 fixture를 저장할 수 있습니다.")
        st.caption("Fixture base dir")
        st.code(fixture_base_dir, language=None)
        return

    with st.expander("Save as fixture", expanded=True):
        case_name = st.text_input("Case name", value=f"{selected.key}_normal")
        description = st.text_area("Description", value=f"{selected.title} 정상 케이스")
        assertion_mode = st.selectbox(
            "Assertion mode",
            ["snapshot", "schema_only", "required_fields", "count"],
        )
        exclude_fields_raw = st.text_input(
            "Exclude fields",
            value="fetched_at, request_id, updated_at",
        )
        required_fields_raw = st.text_input("Required fields", value="")
        overwrite = st.checkbox("Overwrite existing fixture", value=False)

        assertion = {
            "mode": assertion_mode,
            "exclude_fields": [
                value.strip() for value in exclude_fields_raw.split(",") if value.strip()
            ],
            "required_fields": [
                value.strip() for value in required_fields_raw.split(",") if value.strip()
            ],
        }

        st.subheader("Fixture preview")
        st.json(
            {
                "function": selected.key,
                "input": jsonable(run.input),
                "request": jsonable(run.request),
                "response": jsonable(run.response),
                "processed": jsonable(run.processed),
                "assertion": assertion,
            }
        )

        if st.button("Save as fixture"):
            try:
                path = save_fixture(
                    base_dir=fixture_base_dir,
                    function_name=selected.key,
                    case_name=case_name,
                    description=description,
                    input_data=run.input,
                    request_data=run.request,
                    response_data=run.response,
                    parsed_result=run.parsed,
                    processed_result=run.processed,
                    assertion=assertion,
                    overwrite=overwrite,
                )
            except Exception as exc:  # pragma: no cover - UI 표시
                st.error(str(exc))
            else:
                st.success(f"Saved: {path}")


def _fixture_base_dir_sidebar() -> str:
    st.sidebar.subheader("Fixtures")
    candidates = _fixture_dir_candidates()
    options = [str(path) for path in candidates]
    custom_label = "Custom..."
    selected = st.sidebar.selectbox("Fixture base dir", [*options, custom_label])
    if selected == custom_label:
        selected = st.sidebar.text_input(
            "Custom fixture base dir",
            value=str((ROOT / "tests" / "fixtures").resolve()),
        )
    st.sidebar.caption(selected)
    return selected


def _fixture_dir_candidates() -> list[Path]:
    preferred = [
        ROOT / "tests" / "fixtures",
        ROOT / "tests",
        ROOT / "examples",
        ROOT,
    ]
    candidates: list[Path] = []
    for path in preferred:
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _store_run(selected: ApiCatalogEntry, run: DebugRun) -> None:
    runs = st.session_state.setdefault("runs", {})
    runs[_selection_key(selected)] = run


def _current_run(selected: ApiCatalogEntry) -> DebugRun | None:
    runs = st.session_state.get("runs", {})
    result = runs.get(_selection_key(selected))
    return result if isinstance(result, DebugRun) else None


def _selection_key(selected: ApiCatalogEntry) -> str:
    return f"{selected.data_source}:{selected.key}"


if __name__ == "__main__":
    main()
