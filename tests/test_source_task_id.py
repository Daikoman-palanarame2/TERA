from app.schemas.data_contracts import InferenceRequest


def test_inference_request_preserves_official_source_task_id():
    request = InferenceRequest(
        prompt="test",
        task_id="task_10_A0201",
        source_task_id="A02_01",
        c2=10.0,
        c3=100.0,
        lambda_coeff=0.5,
        alpha_dense=0.9,
    )

    assert request.task_id == "task_10_A0201"
    assert request.source_task_id == "A02_01"
