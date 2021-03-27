import pretend

TEST_USER = pretend.stub(name="Name", nick="Nick", id=1123456)


def make_message_stub(content, author=TEST_USER):
    return pretend.stub(content=content, clean_content=content, author=author)
