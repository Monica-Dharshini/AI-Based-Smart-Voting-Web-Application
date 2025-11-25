import face_recognition
import os

def recognize_face(known_image_path, uploaded_image_path):
    """
    Compare the face in uploaded_image_path with the face in known_image_path.

    Returns:
        True if the faces match, False otherwise.
    """
    try:
        # Load known image (user's stored face)
        known_image = face_recognition.load_image_file(known_image_path)
        known_encodings = face_recognition.face_encodings(known_image)

        if not known_encodings:
            print("No face found in known image.")
            return False

        known_encoding = known_encodings[0]

        # Load uploaded image (user's login face)
        uploaded_image = face_recognition.load_image_file(uploaded_image_path)
        uploaded_encodings = face_recognition.face_encodings(uploaded_image)

        if not uploaded_encodings:
            print("No face found in uploaded image.")
            return False

        uploaded_encoding = uploaded_encodings[0]

        # Compare faces
        results = face_recognition.compare_faces([known_encoding], uploaded_encoding)
        return results[0]
    except Exception as e:
        print(f"Error in face recognition: {e}")
        return False
