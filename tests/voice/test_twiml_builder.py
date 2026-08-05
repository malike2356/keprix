from keprix.voice.twiml_builder import connect_stream_response, dial_transfer_response, reject_response


def test_twiml_builders_escape_and_shape_responses() -> None:
    xml = connect_stream_response(stream_url="wss://example.test/voice", greeting="Aiva speaking", call_sid="CA123")

    assert "<Connect>" in xml
    assert 'url="wss://example.test/voice"' in xml
    assert 'name="CA123"' in xml
    assert "Aiva speaking" in xml
    assert "<Reject" in reject_response()
    assert "<Dial>+155501</Dial>" in dial_transfer_response("+155501", "Transfer now")
