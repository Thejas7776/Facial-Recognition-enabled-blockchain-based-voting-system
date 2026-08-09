import cv2
import mediapipe as mp
import numpy as np
import pickle
import os
import logging
import face_recognition

logger = logging.getLogger(__name__)

class FaceRecognitionSystem:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        
        # Initialize face detection and mesh
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.7 # Adjusted confidence for potentially better detection
        )

    def extract_face_encoding(self, image):
        """Extract face bounding box using MediaPipe and then create encoding using face_recognition"""
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 1. Use MediaPipe for initial face detection
            detection_results = self.face_detection.process(rgb_image)
            if not detection_results.detections:
                logger.info("No face detected by MediaPipe (initial detection).")
                return None, None # Return None for encoding and bounding box

            # Assuming one face, take the first detection
            detection = detection_results.detections[0]
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = image.shape
            x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                         int(bboxC.width * iw), int(bboxC.height * ih)
            
            # Define bounding box coordinates (top, right, bottom, left)
            # Face_recognition library uses (top, right, bottom, left) format
            face_bbox = (y, x + w, y + h, x) # (top, right, bottom, left)

            # 2. Crop the face region based on MediaPipe's detection
            face_region = image[y:y+h, x:x+w]
            if face_region.size == 0 or face_region.shape[0] == 0 or face_region.shape[1] == 0:
                logger.warning("Cropped face region is empty or invalid.")
                return None, None

            # 3. Use face_recognition library to find face locations WITHIN the cropped region
            # Convert to RGB for face_recognition
            rgb_face_region = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
            face_locations_in_region = face_recognition.face_locations(rgb_face_region)

            if not face_locations_in_region:
                logger.warning("No face detected by face_recognition within the cropped region.")
                return None, None

            # 4. Generate encoding using face_recognition from the cropped region and its detected locations
            face_encodings = face_recognition.face_encodings(rgb_face_region, face_locations_in_region)

            if face_encodings:
                logger.info("Face encoding extracted successfully from cropped region.")
                logger.debug(f"extract_face_encoding returning: type={type(face_encodings[0])}, shape={face_encodings[0].shape}")
                return face_encodings[0], face_bbox # Return encoding and bounding box
            else:
                logger.warning("Could not generate face encoding from detected face region using face_recognition.")
                return None, None
            
        except Exception as e:
            logging.error(f"Error extracting face encoding: {str(e)}")
            return None, None

    def draw_bounding_box(self, image, bbox, name=None):
        """Draws a bounding box on the image given the bbox in (top, right, bottom, left) format."""
        if bbox:
            top, right, bottom, left = bbox
            # Draw a box around the face
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2) # Green box
            # Draw a label with a name below the face
            if name:
                # Put text above the bounding box
                cv2.rectangle(image, (left, top - 25), (right, top), (0, 255, 0), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(image, name, (left + 6, top - 8), font, 0.5, (255, 255, 255), 1)
            else:
                cv2.rectangle(image, (left, bottom - 15), (right, bottom), (0, 255, 0), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(image, "Face", (left + 6, bottom - 6), font, 0.4, (255, 255, 255), 1)
        return image

    def save_face_encoding(self, encodings, voter_id):
        """Save a list of face encodings (or a single encoding) to a single file for a voter."""
        try:
            file_path = f"face_encodings/{voter_id}.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(encodings, f)
            logger.info(f"Face encoding(s) for voter {voter_id} saved to {file_path}")
            return file_path
        except Exception as e:
            logging.error(f"Error saving face encoding(s) for voter {voter_id}: {str(e)}")
            return None

    def load_face_encoding(self, file_path):
        """Load face encoding from file"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    encoding = pickle.load(f)
                logger.info(f"Face encoding loaded from {file_path}")
                return encoding
            logger.warning(f"Face encoding file not found: {file_path}")
            return None
        except Exception as e:
            logging.error(f"Error loading face encoding from {file_path}: {str(e)}")
            return None

    def compare_faces(self, encoding1, encoding2, threshold=0.7):
        """Compare two face encodings using face_recognition.compare_faces"""
        try:
            if encoding1 is None or encoding2 is None:
                logger.warning("One or both encodings are None, cannot compare.")
                return False
                
            # Ensure encodings are numpy arrays for consistent comparison
            encoding1 = np.array(encoding1)
            encoding2 = np.array(encoding2)
            
            logger.debug(f"Comparing: encoding1 type={type(encoding1)}, shape={encoding1.shape}")
            logger.debug(f"Comparing: encoding2 type={type(encoding2)}, shape={encoding2.shape}")

            # Use face_recognition's comparison function
            # compare_faces returns a list of booleans, face_distance returns array of distances
            matches = face_recognition.compare_faces([encoding1], encoding2, tolerance=threshold)
            # We are interested if there is at least one match
            if True in matches:
                logger.info("Faces matched successfully.")
                return True
            else:
                logger.info("Faces did not match.")
                return False
            
        except Exception as e:
            logging.error(f"Error comparing faces: {str(e)}")
            return False
