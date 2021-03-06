import os
import urllib.parse

import pytest
import salt.utils.json
import salt.utils.stringutils
import tests.support.cherrypy_testclasses as cptc


class TestAuth(cptc.BaseRestCherryPyTest):
    def test_get_root_noauth(self):
        """
        GET requests to the root URL should not require auth
        """
        request, response = self.request("/")
        self.assertEqual(response.status, "200 OK")

    def test_post_root_auth(self):
        """
        POST requests to the root URL redirect to login
        """
        request, response = self.request("/", method="POST", data={})
        self.assertEqual(response.status, "401 Unauthorized")

    def test_login_noauth(self):
        """
        GET requests to the login URL should not require auth
        """
        request, response = self.request("/login")
        self.assertEqual(response.status, "200 OK")

    def test_webhook_auth(self):
        """
        Requests to the webhook URL require auth by default
        """
        request, response = self.request("/hook", method="POST", data={})
        self.assertEqual(response.status, "401 Unauthorized")


class TestLogin(cptc.BaseRestCherryPyTest):
    auth_creds = (("username", "saltdev"), ("password", "saltdev"), ("eauth", "auto"))

    def test_good_login(self):
        """
        Test logging in
        """
        body = urllib.parse.urlencode(self.auth_creds)
        request, response = self.request(
            "/login",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "200 OK")
        return response

    def test_leak(self):
        """
        Test perms leak array is becoming bigger and bigger after each call
        """
        lengthOfPerms = []
        run_tests = 2

        for x in range(0, run_tests):
            body = urllib.parse.urlencode(self.auth_creds)
            request, response = self.request(
                "/login",
                method="POST",
                body=body,
                headers={"content-type": "application/x-www-form-urlencoded"},
            )

            response = salt.utils.json.loads(response.body[0])
            lengthOfPerms.append(len(response["return"][0]["perms"]))
        self.assertEqual(lengthOfPerms[0], lengthOfPerms[run_tests - 1])
        return response

    def test_bad_login(self):
        """
        Test logging in
        """
        body = urllib.parse.urlencode({"totally": "invalid_creds"})
        request, response = self.request(
            "/login",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "401 Unauthorized")

    def test_logout(self):
        ret = self.test_good_login()
        token = ret.headers["X-Auth-Token"]

        body = urllib.parse.urlencode({})
        request, response = self.request(
            "/logout",
            method="POST",
            body=body,
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "X-Auth-Token": token,
            },
        )
        self.assertEqual(response.status, "200 OK")


class TestRun(cptc.BaseRestCherryPyTest):
    auth_creds = (
        ("username", "saltdev_auto"),
        ("password", "saltdev"),
        ("eauth", "auto"),
    )

    low = (
        ("client", "local"),
        ("tgt", "*"),
        ("fun", "test.ping"),
    )

    @pytest.mark.slow_test
    def test_run_good_login(self):
        """
        Test the run URL with good auth credentials
        """
        cmd = dict(self.low, **dict(self.auth_creds))
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "200 OK")

    def test_run_bad_login(self):
        """
        Test the run URL with bad auth credentials
        """
        cmd = dict(self.low, **{"totally": "invalid_creds"})
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "401 Unauthorized")

    def test_run_empty_token(self):
        """
        Test the run URL with empty token
        """
        cmd = dict(self.low, **{"token": ""})
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status == "401 Unauthorized"

    def test_run_empty_token_upercase(self):
        """
        Test the run URL with empty token with upercase characters
        """
        cmd = dict(self.low, **{"ToKen": ""})
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status == "401 Unauthorized"

    def test_run_wrong_token(self):
        """
        Test the run URL with incorrect token
        """
        cmd = dict(self.low, **{"token": "bad"})
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status == "401 Unauthorized"

    def test_run_pathname_token(self):
        """
        Test the run URL with path that exists in token
        """
        cmd = dict(self.low, **{"token": os.path.join("etc", "passwd")})
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status == "401 Unauthorized"

    def test_run_pathname_not_exists_token(self):
        """
        Test the run URL with path that does not exist in token
        """
        cmd = dict(self.low, **{"token": os.path.join("tmp", "doesnotexist")})
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status == "401 Unauthorized"

    @pytest.mark.slow_test
    def test_run_extra_parameters(self):
        """
        Test the run URL with good auth credentials
        """
        cmd = dict(self.low, **dict(self.auth_creds))
        cmd["id_"] = "someminionname"
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "200 OK")


class TestWebhookDisableAuth(cptc.BaseRestCherryPyTest):
    def __get_opts__(self):
        return {
            "rest_cherrypy": {
                "port": 8000,
                "debug": True,
                "webhook_disable_auth": True,
            },
        }

    def test_webhook_noauth(self):
        """
        Auth can be disabled for requests to the webhook URL
        """
        body = urllib.parse.urlencode({"foo": "Foo!"})
        request, response = self.request(
            "/hook",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "200 OK")


class TestArgKwarg(cptc.BaseRestCherryPyTest):
    auth_creds = (("username", "saltdev"), ("password", "saltdev"), ("eauth", "auto"))

    low = (
        ("client", "runner"),
        ("fun", "test.arg"),
        # use singular form for arg and kwarg
        ("arg", [1234]),
        ("kwarg", {"ext_source": "redis"}),
    )

    def _token(self):
        """
        Return the token
        """
        body = urllib.parse.urlencode(self.auth_creds)
        request, response = self.request(
            "/login",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        return response.headers["X-Auth-Token"]

    @pytest.mark.slow_test
    def test_accepts_arg_kwarg_keys(self):
        """
        Ensure that (singular) arg and kwarg keys (for passing parameters)
        are supported by runners.
        """
        cmd = dict(self.low)
        body = salt.utils.json.dumps(cmd)

        request, response = self.request(
            "/",
            method="POST",
            body=body,
            headers={
                "content-type": "application/json",
                "X-Auth-Token": self._token(),
                "Accept": "application/json",
            },
        )
        resp = salt.utils.json.loads(salt.utils.stringutils.to_str(response.body[0]))
        self.assertEqual(resp["return"][0]["args"], [1234])
        self.assertEqual(resp["return"][0]["kwargs"], {"ext_source": "redis"})


class TestJobs(cptc.BaseRestCherryPyTest):
    auth_creds = (
        ("username", "saltdev_auto"),
        ("password", "saltdev"),
        ("eauth", "auto"),
    )

    low = (
        ("client", "local"),
        ("tgt", "*"),
        ("fun", "test.ping"),
    )

    def _token(self):
        """
        Return the token
        """
        body = urllib.parse.urlencode(self.auth_creds)
        request, response = self.request(
            "/login",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        return response.headers["X-Auth-Token"]

    def _add_job(self):
        """
        Helper function to add a job to the job cache
        """
        cmd = dict(self.low, **dict(self.auth_creds))
        body = urllib.parse.urlencode(cmd)

        request, response = self.request(
            "/run",
            method="POST",
            body=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status, "200 OK")

    @pytest.mark.flaky(max_runs=4)
    @pytest.mark.slow_test
    def test_all_jobs(self):
        """
        test query to /jobs returns job data
        """
        self._add_job()

        request, response = self.request(
            "/jobs",
            method="GET",
            headers={"Accept": "application/json", "X-Auth-Token": self._token()},
        )

        resp = salt.utils.json.loads(salt.utils.stringutils.to_str(response.body[0]))
        self.assertIn("test.ping", str(resp["return"]))
        self.assertEqual(response.status, "200 OK")
