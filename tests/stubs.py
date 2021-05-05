import pretend

TEST_USER = pretend.stub(name="Name", nick="Nick", id=1123456)
IRC_USER = pretend.stub(name="irc", nick="irc", id=1337)


def make_message_stub(content, author=TEST_USER):
    return pretend.stub(content=content, clean_content=content, author=author)


def make_irc_message_stub(content):
    message_with_name = f"**<ircname>** {content}"
    return make_message_stub(message_with_name, IRC_USER)
