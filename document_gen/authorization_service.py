# authorization_service.py
class AuthorizationService:
    """
    Dummy authorization service that simulates UPI PIN validation.
    In real UPI, this would verify a secure credential block (CredBlock).
    """

    def __init__(self, default_pin: str = "1234"):
        self.default_pin = default_pin
        # You could add user-specific PIN mapping here if needed

    def authorize(self, vpa: str, pin: str) -> bool:
        """
        Simulates checking a user's UPI PIN for authentication.
        Always returns True if the entered PIN matches default_pin.
        """
        if pin == self.default_pin:
            print(f"[Authorization] PIN verified for {vpa}")
            return True
        else:
            print(f"[Authorization] Invalid PIN for {vpa}")
            return False
