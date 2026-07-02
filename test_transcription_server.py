import requests
import time
import sys

URL_BASE = "http://localhost:9121/api/jobs"

def test_transcription(audio_file_path):
    print(f"Submitting {audio_file_path} to transcription server...")
    with open(audio_file_path, "rb") as f:
        response = requests.post(
            f"{URL_BASE}/submit",
            data={"language": "hi", "user_id": "test_user"},
            files={"audio": f}
        )
    
    if response.status_code != 200:
        print("Failed to submit job:", response.text)
        sys.exit(1)
        
    job_id = response.json()["job_id"]
    print(f"Job submitted successfully. Job ID: {job_id}")
    
    print("Polling for completion...")
    while True:
        status_res = requests.get(f"{URL_BASE}/{job_id}")
        if status_res.status_code == 200:
            job = status_res.json()
            status = job["status"]
            print(f"Status: {status}")
            if status == "completed":
                print("CTC:", job["ctc_transcript"])
                print("RNNT:", job["rnnt_transcript"])
                break
            elif status == "failed":
                print("Job failed.")
                sys.exit(1)
        else:
            print("Error checking status:", status_res.text)
        time.sleep(2)
        
    print("Simulating user selecting RNNT transcript to save permanently...")
    save_res = requests.post(f"{URL_BASE}/{job_id}/save", data={"final_transcript": job["rnnt_transcript"]})
    if save_res.status_code == 200:
        print("Successfully saved final transcript!")
    else:
        print("Failed to save transcript:", save_res.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_transcription_server.py <path_to_audio_file>")
        sys.exit(1)
    test_transcription(sys.argv[1])
