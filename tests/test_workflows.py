from orchestrator.workflows import run_sample_workflow

def test_run_sample_workflow():
    result = run_sample_workflow()
    assert "Processed" in result 