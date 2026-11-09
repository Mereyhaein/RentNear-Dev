from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthApiTests(APITestCase):
    def register(self, **overrides):
        payload = {
            "name": "Merey Zhantuar",
            "email": "merey@example.com",
            "password": "RentNear-pass-19",
            "phone": "+77001234567",
        }
        payload.update(overrides)
        return self.client.post("/api/auth/register", payload, format="json")

    def test_register_creates_account_and_returns_token(self):
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["email"], "merey@example.com")
        self.assertEqual(response.data["user"]["name"], "Merey Zhantuar")
        user = User.objects.get(email="merey@example.com")
        self.assertTrue(user.check_password("RentNear-pass-19"))
        self.assertFalse(user.password.startswith("RentNear"))

    def test_register_rejects_invalid_email(self):
        response = self.register(email="not-an-email")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_register_rejects_short_password(self):
        response = self.register(password="short")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_rejects_duplicate_email(self):
        self.register()
        response = self.register(email="Merey@Example.com", name="Other")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_login_with_correct_credentials(self):
        self.register()
        response = self.client.post(
            "/api/auth/login",
            {"email": "Merey@Example.com", "password": "RentNear-pass-19"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "merey@example.com")
        self.assertTrue(response.data["token"])

    def test_login_with_wrong_password_stays_logged_out(self):
        self.register()
        response = self.client.post(
            "/api/auth/login",
            {"email": "merey@example.com", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Incorrect email or password.")
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_rejects_invalid_email(self):
        response = self.client.post(
            "/api/auth/login",
            {"email": "not-an-email", "password": "RentNear-pass-19"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_token(self):
        registered = self.register()
        token = registered.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, status.HTTP_200_OK)

        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        me_after = self.client.get("/api/auth/me")
        self.assertEqual(me_after.status_code, status.HTTP_401_UNAUTHORIZED)
