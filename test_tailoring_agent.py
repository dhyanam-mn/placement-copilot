import os
import unittest
import shutil
import tempfile
import warnings
from tailoring_agent import tailor_resume, TailoringAgent, parse_tex_template

class TestTailoringAgent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.base_tex = "base_resume.tex"
        cls.keywords_json = "bullet_keywords.json"
        
        cls.cv_jd = """
        We are seeking a Senior Computer Vision Engineer to build real-time object detection systems.
        Key skills required: YOLOv8, PyTorch, GeoTIFF drone imagery processing, rasterio, and OpenCV.
        Experience in image processing and spatial data analytics is highly desirable.
        """
        
        cls.backend_jd = """
        Looking for a Backend Software Engineer to design high-throughput microservices.
        Required: FastAPI, PostgreSQL, Redis caching, REST APIs, distributed systems, and Python.
        Experience with database optimization and SQL scaling.
        """
        
        cls.fullstack_jd = """
        Hiring a Full-Stack Web Developer to create modern web application dashboards.
        Tech Stack: React, TypeScript, Node.js, Express, GraphQL, Tailwind CSS, and frontend state management.
        """

    def test_computer_vision_jd_ranking(self):
        result = tailor_resume(
            jd_text=self.cv_jd,
            tex_path=self.base_tex,
            keywords_path=self.keywords_json,
            output_tex_path="test_output_cv.tex"
        )
        ordered = result["ordered_bullets"]
        self.assertGreater(len(ordered), 0)
        self.assertEqual(ordered[0]["id"], "dronamaps_cv")
        self.assertGreater(ordered[0]["score"], 0.0)
        self.assertTrue(os.path.exists(result["tex_path"]))

    def test_backend_sde_jd_ranking(self):
        result = tailor_resume(
            jd_text=self.backend_jd,
            tex_path=self.base_tex,
            keywords_path=self.keywords_json,
            output_tex_path="test_output_backend.tex"
        )
        ordered = result["ordered_bullets"]
        self.assertGreater(len(ordered), 0)
        self.assertEqual(ordered[0]["id"], "campus_connect_backend")
        self.assertGreater(ordered[0]["score"], 0.0)
        self.assertTrue(os.path.exists(result["tex_path"]))

    def test_fullstack_jd_ranking(self):
        result = tailor_resume(
            jd_text=self.fullstack_jd,
            tex_path=self.base_tex,
            keywords_path=self.keywords_json,
            output_tex_path="test_output_fullstack.tex"
        )
        ordered = result["ordered_bullets"]
        self.assertGreater(len(ordered), 0)
        self.assertEqual(ordered[0]["id"], "fullstack_app")
        self.assertGreater(ordered[0]["score"], 0.0)
        self.assertTrue(os.path.exists(result["tex_path"]))

    def test_content_preservation(self):
        with open(self.base_tex, "r", encoding="utf-8") as f:
            base_content = f.read()
            
        result = tailor_resume(
            jd_text=self.cv_jd,
            tex_path=self.base_tex,
            keywords_path=self.keywords_json,
            output_tex_path="test_output_preserve.tex"
        )
        
        with open(result["tex_path"], "r", encoding="utf-8") as f:
            tailored_content = f.read()
            
        # Verify header and footer are preserved
        header_orig, blocks_orig, footer_orig = parse_tex_template(base_content)
        header_tail, blocks_tail, footer_tail = parse_tex_template(tailored_content)
        
        self.assertEqual(header_orig, header_tail)
        self.assertEqual(footer_orig, footer_tail)
        self.assertEqual(set(blocks_orig.keys()), set(blocks_tail.keys()))
        
        # Verify exact text content of each block is untouched
        for b_id, text in blocks_orig.items():
            self.assertEqual(text.strip(), blocks_tail[b_id].strip())

    def test_pdf_output_generation(self):
        agent = TailoringAgent(tex_path=self.base_tex, keywords_path=self.keywords_json)
        result = agent.tailor(self.cv_jd, output_tex_path="test_output_pdf.tex")
        
        pdf_path = result.get("pdf_path")
        if pdf_path is not None:
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(pdf_path.endswith(".pdf"))
            self.assertGreater(os.path.getsize(pdf_path), 0)
        else:
            warnings.warn("Tectonic CLI not available; skipped PDF output validation.")

    def test_empty_jd(self):
        result = tailor_resume(
            jd_text="",
            tex_path=self.base_tex,
            keywords_path=self.keywords_json,
            output_tex_path="test_output_empty.tex"
        )
        for b in result["ordered_bullets"]:
            self.assertEqual(b["score"], 0.0)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            tailor_resume("sample jd", tex_path="non_existent_file.tex")

    @classmethod
    def tearDownClass(cls):
        # Cleanup temporary test outputs
        for fname in [
            "test_output_cv.tex", "test_output_cv.pdf",
            "test_output_backend.tex", "test_output_backend.pdf",
            "test_output_fullstack.tex", "test_output_fullstack.pdf",
            "test_output_preserve.tex", "test_output_preserve.pdf",
            "test_output_pdf.tex", "test_output_pdf.pdf",
            "test_output_empty.tex", "test_output_empty.pdf"
        ]:
            if os.path.exists(fname):
                try:
                    os.remove(fname)
                except OSError:
                    pass

if __name__ == "__main__":
    unittest.main()
