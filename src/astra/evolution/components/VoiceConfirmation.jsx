/**
 * Voice Confirmation Component
 * ==========================
 * Handles operator voice authorization
 */

import React, { useState, useEffect } from 'react';
import { 
    Box,
    Button,
    Typography,
    CircularProgress
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';

const VoiceConfirmation = ({ onConfirmed }) => {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [error, setError] = useState(null);
    
    useEffect(() => {
        // Initialize speech recognition
        let recognition = null;
        
        if ('webkitSpeechRecognition' in window) {
            recognition = new window.webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                setTranscript(text);
                
                // Check if it matches confirmation phrase
                if (text.toLowerCase().includes('authorized by saint lucid')) {
                    onConfirmed(true);
                    setIsListening(false);
                }
            };
            
            recognition.onerror = (event) => {
                setError(`Speech recognition error: ${event.error}`);
                setIsListening(false);
            };
            
            recognition.onend = () => {
                setIsListening(false);
            };
        }
        
        return () => {
            if (recognition) {
                recognition.abort();
            }
        };
    }, [onConfirmed]);
    
    const startListening = () => {
        setError(null);
        setTranscript('');
        setIsListening(true);
        
        if ('webkitSpeechRecognition' in window) {
            const recognition = new window.webkitSpeechRecognition();
            recognition.start();
        } else {
            setError('Speech recognition not supported in this browser');
        }
    };
    
    return (
        <Box sx={{ mt: 2, p: 2, border: '1px solid #ccc', borderRadius: 1 }}>
            <Typography variant="h6" gutterBottom>
                Voice Authorization
            </Typography>
            
            <Typography variant="body2" color="text.secondary" gutterBottom>
                Please say: "Authorized by Saint Lucid"
            </Typography>
            
            <Button
                variant="contained"
                color={isListening ? 'secondary' : 'primary'}
                startIcon={isListening ? <CircularProgress size={20} /> : <MicIcon />}
                onClick={startListening}
                disabled={isListening}
                sx={{ mt: 1 }}
            >
                {isListening ? 'Listening...' : 'Start Authentication'}
            </Button>
            
            {transcript && (
                <Typography 
                    variant="body2" 
                    sx={{ 
                        mt: 1,
                        p: 1,
                        bgcolor: 'background.paper',
                        borderRadius: 1
                    }}
                >
                    Heard: "{transcript}"
                </Typography>
            )}
            
            {error && (
                <Typography 
                    variant="body2" 
                    color="error"
                    sx={{ mt: 1 }}
                >
                    {error}
                </Typography>
            )}
        </Box>
    );
};

export default VoiceConfirmation;