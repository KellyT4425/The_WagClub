from allauth.account.forms import LoginForm


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "Username"
        self.fields["login"].widget.attrs["placeholder"] = "Username"
