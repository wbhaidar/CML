import unittest
from unittest.mock import patch, Mock
from lab_report import handle_request 

class TestHandleRequest(unittest.TestCase):
    @patch('lab_report.requests.get')
    def test_handle_request_get(self, mock_get):
        """
        Test handle_request function with a GET request.
        """
        mock_response = Mock()
        mock_response.json.return_value = {"message": "success"}
        mock_get.return_value = mock_response
        url = "http://example.com/api"
        
        # Act
        result = handle_request(url, method='get')
        
        # Assert
        mock_get.assert_called_once_with(url, headers=None)  # Ensure GET was called with correct args
        self.assertEqual(result, {"message": "success"})  # Check if return value matches

    @patch('lab_report.requests.post')
    def test_handle_request_post(self, mock_post):
        """
        Test handle_request function with a POST request.
        """
        mock_response = Mock()
        mock_response.json.return_value = {"message": "created"}
        mock_post.return_value = mock_response
        url = "http://example.com/api"
        payload = {"key": "value"}
        
        # Act
        result = handle_request(url, method='post', payload=payload)
        
        # Assert
        mock_post.assert_called_once_with(url, headers=None, json=payload)  # Check POST args
        self.assertEqual(result, {"message": "created"})

    def test_handle_request_invalid_method(self):
        """
        Test handle_request function with an unsupported method.
        """
        url = "http://example.com/api"
        
        # Act & Assert
        with self.assertRaises(ValueError):  # Expect a ValueError for unsupported method
            handle_request(url, method='delete')

if __name__ == '__main__':
    unittest.main()
