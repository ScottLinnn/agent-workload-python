import unittest
import os
import json
from unittest.mock import patch

from agentic_rag.adk.tools import vector_database_search, evaluate_relevance, web_search, submit_final_answer

class TestRagTools(unittest.TestCase):

    @patch('agentic_rag.adk.tools._get_embedding')
    def test_vector_database_search(self, mock_embed):
        # Mock embedding to return a dummy vector of length 768
        mock_embed.return_value = [0.1] * 768
        
        # This will trigger table creation if it doesn't exist
        result = vector_database_search(query="test query", top_k=2)
        
        # Verify result is a JSON string
        self.assertIsInstance(result, str)
        
        try:
            data = json.loads(result)
            self.assertIsInstance(data, list)
            # If table was created, it should have some data
            if len(data) > 0:
                self.assertIn("content", data[0])
                self.assertIn("metadata", data[0])
        except json.JSONDecodeError:
            self.fail("vector_database_search did not return valid JSON")

    def test_evaluate_relevance_relevant(self):
        question = "What is Google ADK?"
        text = "Google ADK is a framework for building agents."
        result_str = evaluate_relevance(question, text)
        result = json.loads(result_str)
        self.assertTrue(result["is_relevant"])

    def test_evaluate_relevance_not_relevant(self):
        question = "What is the weather today?"
        text = "Google ADK is a framework for building agents."
        result_str = evaluate_relevance(question, text)
        result = json.loads(result_str)
        self.assertFalse(result["is_relevant"])
        self.assertIn("missing_information", result)

    def test_web_search(self):
        result_str = web_search("test query")
        result = json.loads(result_str)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("snippet", result[0])

    def test_submit_final_answer(self):
        result = submit_final_answer(final_response="This is the answer.", citations=["source1"])
        self.assertIn("Final answer submitted", result)
        
        # Verify file was created
        results_dir = "adk_rag_agent_results"
        output_file = os.path.join(results_dir, "final_answer.json")
        self.assertTrue(os.path.exists(output_file))
        
        # Clean up
        if os.path.exists(output_file):
            os.remove(output_file)
        if os.path.exists(results_dir) and not os.listdir(results_dir):
            os.rmdir(results_dir)

if __name__ == "__main__":
    unittest.main()
