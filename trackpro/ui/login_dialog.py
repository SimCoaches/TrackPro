# Setup OAuth handler for social logins
self.oauth_handler = OAuthHandler(self)
self.oauth_handler.auth_completed.connect(self.handle_auth_completed)
self.oauth_handler.profile_completion_required.connect(self.handle_profile_completion_required) 