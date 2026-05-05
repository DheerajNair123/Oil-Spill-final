#!/usr/bin/env python3
"""
Live Image Sender for Oil Spill Detector
=========================================
Client-side script for drone/camera/edge devices to capture and send images
to the Flask Oil Spill Detector API endpoint.

Supports:
  - Single image upload
  - Directory polling (watch and send new images)
  - Live webcam streaming
  - Custom location tagging
  - Automatic retry on failure
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_sender.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImageSender:
    """Send images to Oil Spill Detector API with retry logic."""
    
    def __init__(self, api_url: str, api_key: str, timeout: int = 30):
        """
        Initialize sender with API endpoint and authentication.
        
        Args:
            api_url: Base URL of Flask app (e.g., http://localhost:5000)
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create requests session with automatic retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy: 3 retries with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def send_image(
        self,
        image_path: str,
        location_label: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict:
        """
        Send a single image to the API endpoint.
        
        Args:
            image_path: Path to image file
            location_label: Optional location name/description
            latitude: Optional latitude in decimal degrees
            longitude: Optional longitude in decimal degrees
            
        Returns:
            API response as dict
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {'error': 'File not found'}
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {}
                
                if location_label:
                    data['location_label'] = location_label
                if latitude is not None:
                    data['latitude'] = latitude
                if longitude is not None:
                    data['longitude'] = longitude
                
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                logger.info(f"Sending image: {os.path.basename(image_path)}")
                response = self.session.post(
                    f"{self.api_url}/api/predict",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                if 'error' in result:
                    logger.error(f"API error: {result['error']}")
                    return result
                
                # Log successful prediction
                logger.info(
                    f"Prediction: {result.get('prediction')} "
                    f"(confidence: {result.get('confidence', 'N/A'):.2%})"
                )
                if result.get('alert_created'):
                    logger.warning(f"ALERT CREATED! ID: {result.get('alert', {}).get('id')}")
                
                return result
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout - image send failed")
            return {'error': 'Timeout'}
        except requests.exceptions.ConnectionError:
            logger.error("Connection failed - check API URL and network")
            return {'error': 'Connection failed'}
        except Exception as e:
            logger.error(f"Error sending image: {str(e)}")
            return {'error': str(e)}
    
    def send_from_directory(
        self,
        directory: str,
        location_label: Optional[str] = None,
        extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp'),
        poll_interval: int = 5,
        max_retries: int = 2
    ) -> None:
        """
        Monitor directory and send new images as they appear.
        
        Args:
            directory: Directory to monitor for images
            location_label: Optional location tag for all images
            extensions: Tuple of image file extensions to watch
            poll_interval: Seconds between directory checks
            max_retries: Max attempts per image before skipping
        """
        directory = Path(directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return
        
        processed = set()
        logger.info(f"Monitoring directory: {directory}")
        logger.info(f"Poll interval: {poll_interval}s, extensions: {extensions}")
        
        try:
            while True:
                # Find all image files
                current_files = set()
                for ext in extensions:
                    current_files.update(directory.glob(f'*{ext}'))
                    current_files.update(directory.glob(f'*{ext.upper()}'))
                
                # Process new files
                new_files = current_files - processed
                for image_path in sorted(new_files):
                    processed.add(image_path)
                    self.send_image(str(image_path), location_label=location_label)
                    time.sleep(1)  # Small delay between sends
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Directory monitor error: {str(e)}")


def main():
    """CLI interface for image sender."""
    parser = argparse.ArgumentParser(
        description='Send images to Oil Spill Detector API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send a single image
  python image_sender.py --url http://localhost:5000 --key YOUR_API_KEY path/to/image.jpg
  
  # Send with location coordinates
  python image_sender.py --url http://localhost:5000 --key YOUR_API_KEY \\
    --latitude 18.52 --longitude 73.86 path/to/image.jpg
  
  # Monitor a directory for new images
  python image_sender.py --url http://localhost:5000 --key YOUR_API_KEY \\
    --watch ./captures --location "Drone Flight A"
        """
    )
    
    parser.add_argument('image', nargs='?', help='Image file to send')
    parser.add_argument('--url', required=True, help='API base URL (e.g., http://localhost:5000)')
    parser.add_argument('--key', required=True, help='API Key for authentication')
    parser.add_argument('--location', help='Location label/description')
    parser.add_argument('--latitude', type=float, help='Latitude in decimal degrees')
    parser.add_argument('--longitude', type=float, help='Longitude in decimal degrees')
    parser.add_argument('--watch', help='Watch directory for new images (directory polling mode)')
    parser.add_argument('--poll-interval', type=int, default=5, help='Directory poll interval in seconds')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.watch and not args.image:
        parser.error("Either provide an image file or use --watch for directory monitoring")
    
    # Initialize sender
    sender = ImageSender(args.url, args.key, timeout=args.timeout)
    
    try:
        if args.watch:
            # Directory monitoring mode
            sender.send_from_directory(
                args.watch,
                location_label=args.location,
                poll_interval=args.poll_interval
            )
        else:
            # Single image mode
            result = sender.send_image(
                args.image,
                location_label=args.location,
                latitude=args.latitude,
                longitude=args.longitude
            )
            
            # Print result summary
            if 'error' not in result:
                print(f"\nSuccess!")
                print(f"  Prediction: {result.get('prediction')}")
                print(f"  Confidence: {result.get('confidence', 'N/A'):.2%}")
                print(f"  Image URL: {result.get('image_url')}")
                if result.get('alert_created'):
                    print(f"  Alert ID: {result.get('alert', {}).get('id')}")
            else:
                print(f"\nError: {result.get('error')}")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
