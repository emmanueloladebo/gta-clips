import sys
from workers.facecam_detector import facecam_detector
from workers.candidate_worker import GroqCandidateWorker

def check():
    print("=== System Verification ===")
    print("Facecam cascade ready:", facecam_detector.cascade is not None)
    
    worker = GroqCandidateWorker()
    print("Groq model:", worker.model_id)
    print("Groq mock mode:", worker.mock_mode)

if __name__ == "__main__":
    check()
