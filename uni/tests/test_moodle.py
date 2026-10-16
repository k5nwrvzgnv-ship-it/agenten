import unittest

import moodle


class TestMoodleMitToken(unittest.TestCase):
    def test_fristen_mit_praefix(self):
        m = moodle.MoodleMitToken("https://moodle.test/", "t", praefix="bfh-")
        antworten = {
            "mod_assign_get_assignments": {"courses": [{"id": 1, "fullname": "K", "assignments": [
                {"id": 5, "cmid": 7, "name": "A", "duedate": 200, "cutoffdate": 0, "teamsubmission": 1}]}]},
            "core_webservice_get_site_info": {"userid": 3},
            "core_group_get_course_user_groups": {"groups": []},
            "mod_assign_get_submission_status": {"lastattempt": {"submission": {"status": "new"}}},
            "mod_quiz_get_quizzes_by_courses": {"quizzes": []},
        }
        m.aufruf = lambda funktion, **p: antworten[funktion]
        f = m.fristen(100)
        self.assertEqual(f[0]["id"], "bfh-assign-5")
        self.assertTrue(f[0]["ohne_gruppe"])
        self.assertEqual(f[0]["url"], "https://moodle.test/mod/assign/view.php?id=7")
        self.assertEqual(m.token(), "t")

    def test_abgelaufener_schluessel(self):
        m = moodle.MoodleMitToken("https://moodle.test", "t", praefix="bfh-")
        moodle_post = moodle._post
        moodle._post = lambda url, daten: {"exception": "x", "errorcode": "invalidtoken", "message": "Ungültig"}
        try:
            with self.assertRaisesRegex(moodle.MoodleFehler, "neu holen"):
                m.aufruf("core_webservice_get_site_info")
        finally:
            moodle._post = moodle_post

    def test_hnee_ohne_praefix(self):
        self.assertEqual(moodle.Moodle.praefix, "")
