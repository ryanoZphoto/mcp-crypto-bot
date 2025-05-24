from orchestrator import workflows


def test_run_sample_workflow(monkeypatch):
    def mock_get_new_sheet_rows(symbol="BTC"):
        return [(symbol, "12345.67")]

    messages = []
    def mock_send_slack_message(message):
        messages.append(message)
        return True

    monkeypatch.setattr(workflows, "get_new_sheet_rows", mock_get_new_sheet_rows)
    monkeypatch.setattr(workflows, "send_slack_message", mock_send_slack_message)

    result = workflows.run_sample_workflow("BTC")
    assert "Current BTC price" in result
    assert messages, "Slack message should be sent"
