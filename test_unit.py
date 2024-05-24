import unittest
from unittest.mock import MagicMock, patch
from app import get_user_info, server

class UserInfo(unittest.TestCase):

    def setUp(self):
        self.mock_cursor = MagicMock()

    def test_id_valid(self):
        self.mock_cursor.fetchall.side_effect = [
            [{'name': 'John Doe'}], 
            [{'job_code': '123'}, {'job_code': '456'}]
        ]
        user_info = get_user_info(1, self.mock_cursor)
        self.assertEqual(user_info['name'], 'John Doe')
        self.assertEqual(user_info['bookmark_list'], ['123', '456'])

    def test_id_none(self):
        self.mock_cursor.fetchall.return_value = []
        user_info = get_user_info(None, self.mock_cursor)
        self.assertIsNone(user_info['name'])
        self.assertIsNone(user_info['bookmark_list'])

class TestAPIs(unittest.TestCase):

    def setUp(self):
        server.testing = True
        self.app = server.test_client()

    @patch('app.connect_db')
    def test_display_region_salary(self, mock_connect_db):
        mock_cursor = MagicMock()
        mock_connect_db.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'region': '台北市', 'region_average': 120000},
            {'region': '新北市', 'region_average': 110000}
        ]
        for data in [{'input_text': '前端工程師'}, {}]:
            response = self.app.post('/api/dashboard/region_salary', json=data)
            response_data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response_data['region'], ['台北市 ', '新北市 '])
            self.assertEqual(response_data['region_average'], [120000, 110000])

    @patch('app.connect_db')
    def test_display_edu_level(self, mock_connect_db):
        mock_cursor = MagicMock()
        mock_connect_db.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'min_edu_level': '大學', 'count': 50},
            {'min_edu_level': '碩士', 'count': 30}
        ]
        for data in [{'input_text': '後端工程師'}, {}]:
            response = self.app.post('/api/dashboard/edu_level', json=data)
            response_data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response_data['labels'], ['大學', '碩士'])
            self.assertEqual(response_data['values'], [50, 30])

class GetJD(unittest.TestCase):

    def setUp(self):
        server.testing = True
        self.app = server.test_client()

    @patch('app.get_user_info')
    @patch('app.conn.cursor')
    def test_jd_exist(self, mock_cursor, mock_get_user_info):
        mock_get_user_info.return_value = {'name': 'yoli', 'bookmark_list': ['78pf4', '75502276']}
        cursor_mock_instance = MagicMock()
        mock_cursor.return_value = cursor_mock_instance
        cursor_mock_instance.fetchall.return_value = [
            {'job_code': '8aary', 'job_title': 'APP應用工程師', 'company_name': '志合訊息股份有限公司', 'job_location': '台北市內湖區'},
            {'job_code': '75589156', 'job_title': '數位商業分析師', 'company_name': 'AXA Hong Kong', 'job_location': '香港南區黃竹坑'},
            {'job_code': 'yEO595', 'job_title': '【總公司】軟體設計工程師', 'company_name': '築間餐飲事業股份有限公司', 'job_location': '台中市西屯區台灣大道三段789號'}
        ]
        response = self.app.get('/job/8aary')
        self.assertEqual(response.status_code, 200)
        self.assertIn('APP應用工程師', response.data.decode('utf-8'))

    @patch('app.get_user_info')
    @patch('app.conn.cursor')
    def test_jd_nonexist(self, mock_cursor, mock_get_user_info):
        mock_get_user_info.return_value = {'name': 'yoli', 'bookmark_list': ['78pf4', '75502276']}
        cursor_mock_instance = MagicMock()
        mock_cursor.return_value = cursor_mock_instance
        cursor_mock_instance.fetchall.return_value = []
        response = self.app.get('/job/12345')
        self.assertEqual(response.status_code, 404)

class TestSignup(unittest.TestCase):
    def setUp(self):
        server.config['TESTING'] = True
        self.app = server.test_client()

    def test_valid_signup(self):
        data = {'name': 'caroline', 'email': 'caroline@gmail.com', 'password': 'carochan$9*x'}
        response = self.app.post('/api/user/signup', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_invalid_email_signup(self):
        data = {'name': 'invalid_email', 'email': 'invalid_email.com', 'password': 'Test@Password1'}
        response = self.app.post('/api/user/signup', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email format', response.data)

    def test_invalid_password_signup(self):
        data = {'name': 'Test User', 'email': 'test@example.com', 'password': 'short'}
        response = self.app.post('/api/user/signup', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password must be at least 8 characters long', response.data)

class TestSearchJobsGet(unittest.TestCase):

    def setUp(self):
        server.testing = True
        self.app = server.test_client()

    @patch('app.get_user_info')
    @patch('app.conn.cursor')
    def test_search_jobs_valid(self, mock_cursor, mock_get_user_info):
        mock_get_user_info.return_value = {'name': 'John Doe', 'bookmark_list': ['job1', 'job2']}
        mock_cursor.return_value.fetchall.return_value = [
            {'job_title': 'Software Engineer', 'company_name': 'Company A', 'job_location': 'Location A', 'salary_period': 'monthly', 'job_source': 'source', 'job_code': 'job1'}
        ]

        response = self.app.get('/job/search?keyword=Engineer&job_title=Software&salary=50000&location=A&user_id=1')

        self.assertEqual(response.status_code, 200)
        data = response.data.decode('utf-8')
        self.assertIn('Software Engineer', data)
        self.assertIn('Company A', data)
        self.assertIn('John Doe', data)

    @patch('app.get_user_info')
    @patch('app.conn.cursor')
    def test_search_jobs_invalid(self, mock_cursor, mock_get_user_info):
        mock_get_user_info.return_value = {'name': 'John Doe', 'bookmark_list': ['job1', 'job2']}
        mock_cursor.return_value.fetchall.return_value = []

        response = self.app.get('/job/search?keyword=NonExistentJob&job_title=NonExistent&salary=50000&location=Nowhere')

        self.assertEqual(response.status_code, 200)
        data = response.data.decode('utf-8')
        self.assertIn('No matching search results', data)

if __name__ == '__main__':
    unittest.main()
