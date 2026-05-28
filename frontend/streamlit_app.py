from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "input"
DEFAULT_BACKEND_URL = os.environ.get("WEALTH_ADVISOR_API_BASE_URL", "http://127.0.0.1:8000")


@st.cache_resource
def get_http_client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


def api_url(backend_url: str, path: str) -> str:
    return f"{backend_url.rstrip('/')}{path}"


def read_sample_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.json"))


def load_json_text(raw_text: str) -> dict[str, Any]:
    return json.loads(raw_text)


def check_backend(backend_url: str) -> dict[str, Any]:
    client = get_http_client()
    response = client.get(api_url(backend_url, "/health"))
    response.raise_for_status()
    return response.json()


def submit_analysis(backend_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = get_http_client()
    response = client.post(api_url(backend_url, "/analysis"), json=payload)
    response.raise_for_status()
    return response.json()


def approve_analysis(backend_url: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = get_http_client()
    response = client.post(api_url(backend_url, f"/analysis/{run_id}/approval"), json=payload)
    response.raise_for_status()
    return response.json()


def fetch_run(backend_url: str, run_id: str) -> dict[str, Any]:
    client = get_http_client()
    response = client.get(api_url(backend_url, f"/analysis/{run_id}"))
    response.raise_for_status()
    return response.json()


def render_input_panel(backend_url: str) -> None:
    st.subheader("Input")
    sample_files = read_sample_files(INPUT_DIR)
    sample_names = [path.name for path in sample_files]
    selected_name = st.selectbox("Sample file", sample_names if sample_names else ["No input files found"])

    file_text = ""
    if sample_files:
        selected_path = INPUT_DIR / selected_name
        file_text = selected_path.read_text(encoding="utf-8")

    # uploaded = st.file_uploader("Or upload a JSON file", type=["json"])
    # if uploaded is not None:
    #     file_text = uploaded.read().decode("utf-8")

    input_text = st.text_area("Client payload", value=file_text, height=420)

    if st.button("Run analysis"):
        try:
            payload = load_json_text(input_text)
            response = submit_analysis(backend_url, payload)
            st.session_state["last_response"] = response
            st.session_state["last_run_id"] = response["run_id"]
            st.success(f"Analysis complete for {response['run_id']}")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))


def render_output_panel(backend_url: str) -> None:
    st.subheader("Output")
    last_response = st.session_state.get("last_response")
    if not last_response:
        st.info("Run an analysis to see the result here.")
        return

    run_id = last_response["run_id"]
    output_col, approval_col = st.columns([1.4, 1])

    with output_col:
        st.json(last_response)
        st.caption(f"Stored run artifact: {REPO_ROOT / 'output' / 'runs' / f'{run_id}.json'}")

        if st.button("Refresh Output", key=f"refresh_{run_id}"):
            try:
                st.session_state["last_response"] = fetch_run(backend_url, run_id)
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    with approval_col:
        if last_response.get("status") == "awaiting_approval":
            st.subheader("Approval")
            decision = st.selectbox("Decision", ["approved", "rejected", "overridden"], key=f"decision_{run_id}")
            reviewer = st.text_input("Reviewer", value="advisor", key=f"reviewer_{run_id}")
            notes = st.text_area("Reviewer notes", key=f"notes_{run_id}")

            override_action = None
            override_rationale = None
            override_priority = None
            override_next_steps = None
            override_risk_flags = None

            if decision == "overridden":
                override_action = st.text_input("Override action", key=f"override_action_{run_id}")
                override_rationale = st.text_area("Override rationale", key=f"override_rationale_{run_id}")
                override_priority = st.selectbox("Override priority", ["low", "medium", "high"], key=f"override_priority_{run_id}")
                override_next_steps_text = st.text_area("Override next steps (one per line)", key=f"override_next_steps_{run_id}")
                override_risk_flags_text = st.text_area("Override risk flags (one per line)", key=f"override_risk_flags_{run_id}")
                override_next_steps = [line.strip() for line in override_next_steps_text.splitlines() if line.strip()]
                override_risk_flags = [line.strip() for line in override_risk_flags_text.splitlines() if line.strip()]

            if st.button("Submit approval", key=f"approve_{run_id}"):
                try:
                    payload = {
                        "decision": decision,
                        "reviewer": reviewer,
                        "notes": notes or None,
                        "override_action": override_action or None,
                        "override_rationale": override_rationale or None,
                        "override_priority": override_priority,
                        "override_next_steps": override_next_steps,
                        "override_risk_flags": override_risk_flags,
                    }
                    response = approve_analysis(backend_url, run_id, payload)
                    st.session_state["last_response"] = response
                    st.success(f"Run {run_id} updated")
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))


def main() -> None:
    st.set_page_config(page_title="Wealth Advisor Assistant", layout="wide")
    st.title("Wealth Advisor Assistant")
    st.caption("Frontend-only Streamlit app that talks to the FastAPI backend over HTTP.")

    st.sidebar.header("How to use")
    st.sidebar.markdown(
        """
        1. Select a client JSON.
        2. Run the analysis from the left panel.
        3. Review results and submit approval on the right.
        4. Press the "Refresh Output" button to see the updated run record after approval.
        """
    )
    backend_url = DEFAULT_BACKEND_URL

    left, right = st.columns([1, 1])
    with left:
        render_input_panel(backend_url)
    with right:
        render_output_panel(backend_url)


if __name__ == "__main__":
    main()
