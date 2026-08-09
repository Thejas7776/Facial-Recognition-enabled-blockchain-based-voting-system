// Face capture functionality for admin voter registration
let stream = null;
let faceDataCaptured = false;

document.addEventListener('DOMContentLoaded', function() {
    const startCameraBtn = document.getElementById('start-camera');
    const captureBtn = document.getElementById('capture-btn');
    const stopCameraBtn = document.getElementById('stop-camera');
    const retakeBtn = document.getElementById('retake-btn');
    const submitBtn = document.getElementById('submit-btn');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const capturedImg = document.getElementById('captured-img');
    const faceDataInput = document.getElementById('face_data');

    // Start camera
    startCameraBtn.addEventListener('click', async function() {
        try {
            // Request camera access
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: 640, 
                    height: 480,
                    facingMode: 'user' // Front camera for selfies
                } 
            });
            
            video.srcObject = stream;
            
            // Hide start button, show video container
            document.getElementById('camera-section').querySelector('div').style.display = 'none';
            document.getElementById('video-container').classList.remove('hidden');
            
            // Show face detection status
            document.getElementById('face-status').classList.remove('hidden');
            
        } catch (error) {
            console.error('Camera access error:', error);
            showError('Camera access denied or not available. Please check your camera permissions.');
        }
    });

    // Capture photo
    captureBtn.addEventListener('click', function() {
        if (!stream) {
            showError('Camera not active. Please start camera first.');
            return;
        }

        const context = canvas.getContext('2d');
        
        // Set canvas size to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw current video frame to canvas (flip horizontally for natural selfie view)
        context.scale(-1, 1);
        context.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
        context.setTransform(1, 0, 0, 1, 0, 0); // Reset transformation
        
        // Convert to base64 image data
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Store face data
        faceDataInput.value = imageData;
        faceDataCaptured = true;
        
        // Show captured image
        capturedImg.src = imageData;
        
        // Hide video container, show captured section
        document.getElementById('video-container').classList.add('hidden');
        document.getElementById('captured-section').classList.remove('hidden');
        
        // Enable submit button
        updateSubmitButton();
        
        // Stop camera stream
        stopCamera();
        
        showSuccess('Face captured successfully! You can now submit the registration form.');
    });

    // Stop camera
    stopCameraBtn.addEventListener('click', function() {
        stopCamera();
        document.getElementById('video-container').classList.add('hidden');
        document.getElementById('camera-section').querySelector('div').style.display = 'block';
    });

    // Retake photo
    retakeBtn.addEventListener('click', function() {
        // Clear captured data
        faceDataInput.value = '';
        faceDataCaptured = false;
        
        // Hide captured section
        document.getElementById('captured-section').classList.add('hidden');
        
        // Show camera start button
        document.getElementById('camera-section').querySelector('div').style.display = 'block';
        
        // Update submit button
        updateSubmitButton();
    });

    // Form validation
    const form = document.getElementById('registration-form');
    const requiredFields = ['name', 'phone', 'address', 'gender', 'birthdate'];
    
    requiredFields.forEach(fieldName => {
        const field = document.getElementById(fieldName);
        if (field) {
            field.addEventListener('input', updateSubmitButton);
            field.addEventListener('change', updateSubmitButton);
        }
    });

    // Form submission
    form.addEventListener('submit', function(e) {
        if (!validateForm()) {
            e.preventDefault();
            return false;
        }
        
        // Show loading state
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
        submitBtn.disabled = true;
    });

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => {
                track.stop();
            });
            stream = null;
        }
    }

    function updateSubmitButton() {
        const isFormValid = validateForm();
        
        if (isFormValid && faceDataCaptured) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('bg-gray-400');
            submitBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
            submitBtn.innerHTML = '<i class="fas fa-user-plus mr-2"></i>Register Voter';
        } else {
            submitBtn.disabled = true;
            submitBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            submitBtn.classList.add('bg-gray-400');
            
            if (!faceDataCaptured) {
                submitBtn.innerHTML = '<i class="fas fa-camera mr-2"></i>Face Capture Required';
            } else {
                submitBtn.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i>Complete All Fields';
            }
        }
    }

    function validateForm() {
        let isValid = true;
        
        requiredFields.forEach(fieldName => {
            const field = document.getElementById(fieldName);
            if (field && !field.value.trim()) {
                isValid = false;
            }
        });
        
        // Validate phone number format
        const phoneField = document.getElementById('phone');
        if (phoneField && phoneField.value) {
            const phoneRegex = /^[+]?[0-9]{10,15}$/;
            if (!phoneRegex.test(phoneField.value.replace(/\s/g, ''))) {
                isValid = false;
            }
        }
        
        // Validate birthdate (must be at least 18 years old)
        const birthdateField = document.getElementById('birthdate');
        if (birthdateField && birthdateField.value) {
            const birthDate = new Date(birthdateField.value);
            const today = new Date();
            const age = today.getFullYear() - birthDate.getFullYear();
            const monthDiff = today.getMonth() - birthDate.getMonth();
            
            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
                age--;
            }
            
            if (age < 18) {
                isValid = false;
                showError('Voter must be at least 18 years old.');
            }
        }
        
        return isValid;
    }

    function showError(message) {
        // Create or update error notification
        removeExistingNotifications();
        
        const notification = document.createElement('div');
        notification.className = 'fixed top-20 right-4 z-50 bg-red-100 border border-red-400 text-red-700 px-6 py-4 rounded-lg shadow-lg max-w-sm animate-slide-in';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-lg leading-none">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    function showSuccess(message) {
        // Create or update success notification
        removeExistingNotifications();
        
        const notification = document.createElement('div');
        notification.className = 'fixed top-20 right-4 z-50 bg-green-100 border border-green-400 text-green-700 px-6 py-4 rounded-lg shadow-lg max-w-sm animate-slide-in';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-check-circle mr-2"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-lg leading-none">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }

    function removeExistingNotifications() {
        const existingNotifications = document.querySelectorAll('.fixed.top-20.right-4');
        existingNotifications.forEach(notification => {
            if (notification.classList.contains('bg-red-100') || notification.classList.contains('bg-green-100')) {
                notification.remove();
            }
        });
    }

    // Handle browser compatibility
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        startCameraBtn.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i>Camera Not Supported';
        startCameraBtn.disabled = true;
        showError('Camera is not supported in this browser. Please use a modern browser like Chrome, Firefox, or Safari.');
    }

    // Handle page unload - stop camera
    window.addEventListener('beforeunload', function() {
        stopCamera();
    });

    // Initialize submit button state
    updateSubmitButton();
});

// Additional utility functions for face detection feedback
function detectFaceInVideo(video, callback) {
    // This is a simple implementation - the actual face detection
    // happens on the server side with MediaPipe
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    context.drawImage(video, 0, 0);
    
    // Simple brightness detection as a proxy for face presence
    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    let brightness = 0;
    
    for (let i = 0; i < data.length; i += 4) {
        brightness += (data[i] + data[i + 1] + data[i + 2]) / 3;
    }
    
    brightness = brightness / (canvas.width * canvas.height);
    
    // If brightness is reasonable, assume face might be present
    const faceDetected = brightness > 50 && brightness < 200;
    callback(faceDetected);
}

// Add visual feedback for face positioning
function addFaceGuide() {
    const videoContainer = document.getElementById('video-container');
    if (!videoContainer.querySelector('.face-guide')) {
        const guide = document.createElement('div');
        guide.className = 'face-guide absolute inset-0 pointer-events-none';
        guide.innerHTML = `
            <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-48 h-60 border-4 border-blue-500 border-dashed rounded-full opacity-50">
                <div class="text-center mt-64 text-blue-600 font-semibold text-sm">
                    Position your face here
                </div>
            </div>
        `;
        videoContainer.style.position = 'relative';
        videoContainer.appendChild(guide);
    }
}
