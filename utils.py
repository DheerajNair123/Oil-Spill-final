import os
import cv2
import numpy as np
import json
import time
from PIL import Image
from datetime import datetime
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from models import db, Prediction, ModelMetrics, AuditLog

class PredictionService:
    """Service for making and managing predictions"""
    
    def __init__(self, model):
        self.model = model
        self.input_size = 224
        
    def predict_image(self, image_path):
        """
        Make prediction on a single image
        Returns: (label, confidence, raw_value, processing_time)
        """
        start_time = time.time()
        
        try:
            # Load and preprocess image
            img = Image.open(image_path).convert("RGB")
            img = img.resize((self.input_size, self.input_size))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            # Make prediction
            prediction = self.model.predict(img_array, verbose=0)[0][0]
            
            # Determine label and confidence
            label = "Oil Spill" if prediction >= 0.5 else "No Oil Spill"
            confidence = float(prediction) if prediction >= 0.5 else float(1 - prediction)
            
            processing_time = time.time() - start_time
            
            return {
                'label': label,
                'confidence': confidence,
                'raw_value': float(prediction),
                'processing_time': processing_time,
                'success': True
            }
        
        except Exception as e:
            return {
                'label': None,
                'confidence': None,
                'raw_value': None,
                'processing_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
    
    def save_prediction(self, user_id, image_filename, image_path, label, confidence, raw_value, processing_time):
        """Save prediction to database"""
        try:
            prediction = Prediction(
                user_id=user_id,
                image_filename=image_filename,
                image_path=image_path,
                prediction_label=label,
                confidence_score=confidence,
                raw_prediction_value=raw_value,
                processing_time=processing_time,
                processed=True
            )
            db.session.add(prediction)
            db.session.commit()
            return prediction
        except Exception as e:
            db.session.rollback()
            raise e
    
    def update_prediction_feedback(self, prediction_id, feedback):
        """Update prediction feedback"""
        try:
            prediction = Prediction.query.get(prediction_id)
            if prediction:
                prediction.feedback = feedback
                prediction.feedback_timestamp = datetime.utcnow()
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e


class ImageProcessing:
    """Image preprocessing utilities"""
    
    @staticmethod
    def enhance_contrast(image_path, output_path=None):
        """Enhance image contrast using CLAHE"""
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge and convert back to BGR
        processed = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
        
        if output_path:
            cv2.imwrite(output_path, enhanced)
        
        return enhanced
    
    @staticmethod
    def denoise(image_path, output_path=None):
        """Remove noise from image"""
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Apply non-local means denoising
        denoised = cv2.fastNlMeansDenoisingColored(img, None, h=10, hForColorComponents=10, templateWindowSize=7, searchWindowSize=21)
        
        if output_path:
            cv2.imwrite(output_path, denoised)
        
        return denoised
    
    @staticmethod
    def resize_image(image_path, target_size=(224, 224)):
        """Resize image to target size"""
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        resized = cv2.resize(img, target_size)
        return resized
    
    @staticmethod
    def preprocess_pipeline(image_path, enhance=True, denoise=True):
        """Complete preprocessing pipeline"""
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        if denoise:
            img = cv2.fastNlMeansDenoisingColored(img, None, h=10, hForColorComponents=10, templateWindowSize=7, searchWindowSize=21)
        
        if enhance:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            img = cv2.merge([l, a, b])
            img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
        
        return img


class AnalyticsService:
    """Service for generating analytics and metrics"""
    
    @staticmethod
    def get_user_accuracy(user_id):
        """Get user's prediction accuracy"""
        predictions = Prediction.query.filter_by(user_id=user_id).all()
        if not predictions:
            return None
        
        feedback_predictions = [p for p in predictions if p.feedback is not None]
        if not feedback_predictions:
            return None
        
        correct = sum(1 for p in feedback_predictions if p.feedback is True)
        return round((correct / len(feedback_predictions)) * 100, 2)
    
    @staticmethod
    def get_model_statistics():
        """Get overall model statistics"""
        predictions = Prediction.query.all()
        
        if not predictions:
            return {
                'total_predictions': 0,
                'oil_spill_count': 0,
                'no_oil_spill_count': 0,
                'average_confidence': 0,
                'feedback_count': 0,
                'accuracy': 0
            }
        
        oil_spill_count = sum(1 for p in predictions if p.prediction_label == 'Oil Spill')
        no_oil_spill_count = sum(1 for p in predictions if p.prediction_label == 'No Oil Spill')
        avg_confidence = np.mean([p.confidence_score for p in predictions])
        
        feedback_predictions = [p for p in predictions if p.feedback is not None]
        feedback_count = len(feedback_predictions)
        accuracy = 0
        
        if feedback_count > 0:
            correct = sum(1 for p in feedback_predictions if p.feedback is True)
            accuracy = round((correct / feedback_count) * 100, 2)
        
        return {
            'total_predictions': len(predictions),
            'oil_spill_count': oil_spill_count,
            'no_oil_spill_count': no_oil_spill_count,
            'average_confidence': float(avg_confidence),
            'feedback_count': feedback_count,
            'accuracy': accuracy
        }
    
    @staticmethod
    def get_predictions_by_date(days=30):
        """Get predictions grouped by date (last N days)"""
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        predictions = Prediction.query.filter(Prediction.created_at >= start_date).all()
        
        date_dict = {}
        for pred in predictions:
            date_key = pred.created_at.date().isoformat()
            if date_key not in date_dict:
                date_dict[date_key] = {'oil_spill': 0, 'no_oil_spill': 0}
            
            if pred.prediction_label == 'Oil Spill':
                date_dict[date_key]['oil_spill'] += 1
            else:
                date_dict[date_key]['no_oil_spill'] += 1
        
        return date_dict
    
    @staticmethod
    def export_statistics_json():
        """Export statistics as JSON"""
        stats = AnalyticsService.get_model_statistics()
        stats['by_date'] = AnalyticsService.get_predictions_by_date(30)
        return stats


def log_audit_action(user_id, action, resource_type, resource_id=None, details=None, ip_address=None):
    """Log an audit action"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error logging audit action: {e}")


def generate_api_key():
    """Generate a secure API key"""
    import secrets
    return secrets.token_urlsafe(32)
