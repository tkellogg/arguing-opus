import os
import tempfile
import unittest
import shutil
from pathlib import Path
import publish

class TestPublish(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a test HTML file
        self.test_html = Path(self.test_dir) / "test_debate.html"
        with open(self.test_html, "w") as f:
            f.write("<html><body>Test debate</body></html>")
            
    def tearDown(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)
            
    def test_publish_file(self):
        # Run the publish function
        import sys
        sys.argv = ["publish.py", str(self.test_html)]
        publish.main()
        
        # Check if published directory was created
        published_dir = Path(self.test_dir) / "published"
        self.assertTrue(published_dir.exists())
        
        # Check if file was copied
        published_file = published_dir / "test_debate.html"
        self.assertTrue(published_file.exists())
        
        # Check if index.html was created and contains the link
        index_path = published_dir / "index.html"
        self.assertTrue(index_path.exists())
        
        with open(index_path, "r") as f:
            content = f.read()
            self.assertIn("test_debate.html", content)

if __name__ == "__main__":
    unittest.main()