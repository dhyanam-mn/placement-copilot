import unittest
from scam_check import check_scam

class TestScamCheck(unittest.TestCase):

    def test_legitimate_contact(self):
        payload = {
            "sender_email": "recruiter@google.com",
            "claimed_company": "Google",
            "message_text": "Hi Dhyanam, we reviewed your application for Software Engineer and would like to schedule a technical interview next week."
        }
        res = check_scam(input_data=payload)
        
        self.assertIn("risk_score", res)
        self.assertIn("flagged_reasons", res)
        self.assertIn("explanation_text", res)
        
        self.assertAlmostEqual(res["risk_score"], 0.0, delta=0.1)
        self.assertEqual(res["flagged_reasons"], [])
        self.assertIsNone(res["explanation_text"])

    def test_obvious_scam(self):
        payload = {
            "sender_email": "hr@technova-careers.in",
            "claimed_company": "TechNova Solutions",
            "message_text": "Urgent: You have been selected! Please respond within 24 hours and pay a registration fee of $50 before interview. Contact us on Telegram."
        }
        res = check_scam(input_data=payload)
        
        self.assertGreaterEqual(res["risk_score"], 0.7)
        self.assertGreaterEqual(len(res["flagged_reasons"]), 3)
        self.assertIsNone(res["explanation_text"])
        
        reasons_text = " ".join(res["flagged_reasons"]).lower()
        self.assertIn("technova-careers.in", reasons_text)
        self.assertIn("registration fee", reasons_text)
        self.assertIn("urgent", reasons_text)
        self.assertIn("telegram", reasons_text)

    def test_ambiguous_contact(self):
        payload = {
            "sender_email": "recruiter.john@gmail.com",
            "claimed_company": "Razorpay",
            "message_text": "Hi Dhyanam, thank you for applying to Razorpay. We would love to set up an introductory call to discuss your profile."
        }
        res = check_scam(input_data=payload)
        
        self.assertTrue(0.2 <= res["risk_score"] <= 0.5)
        self.assertEqual(len(res["flagged_reasons"]), 1)
        self.assertIn("public email domain", res["flagged_reasons"][0])
        self.assertIsNone(res["explanation_text"])

    def test_positional_vs_dict_input(self):
        res_dict = check_scam(input_data={
            "sender_email": "fake@razorpay-jobs.org",
            "claimed_company": "Razorpay",
            "message_text": "Pay refundable fee now."
        })
        res_pos = check_scam(
            sender_email="fake@razorpay-jobs.org",
            claimed_company="Razorpay",
            message_text="Pay refundable fee now."
        )
        
        self.assertEqual(res_dict, res_pos)
        self.assertIsNone(res_dict["explanation_text"])

    def test_output_shape_contract(self):
        res = check_scam(sender_email="a@b.com", claimed_company="B", message_text="Hello")
        self.assertSetEqual(set(res.keys()), {"risk_score", "flagged_reasons", "explanation_text"})
        self.assertIsInstance(res["risk_score"], float)
        self.assertIsInstance(res["flagged_reasons"], list)
        self.assertIsNone(res["explanation_text"])

if __name__ == "__main__":
    unittest.main()
