/**
 * ASTRA Evolution Modal v2 UI Component
 * ===================================
 * Author: Saint Lucid
 * Date: October 22, 2025
 * Sacred Code: 333
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    Modal,
    Box,
    Typography,
    Button,
    LinearProgress,
    Grid,
    Paper
} from '@mui/material';
import {
    Timeline,
    TimelineItem,
    TimelineSeparator,
    TimelineConnector,
    TimelineContent,
    TimelineDot
} from '@mui/lab';

// Custom components
import HeatmapVisualizer from './HeatmapVisualizer';
import TelemetryDashboard from './TelemetryDashboard';
import SimulationPanel from './SimulationPanel';
import VoiceConfirmation from './VoiceConfirmation';

const evolutionStages = [
    { id: 'propose', label: 'Propose', icon: '📝' },
    { id: 'simulate', label: 'Simulate', icon: '🔬' },
    { id: 'validate', label: 'Validate', icon: '✅' },
    { id: 'commit', label: 'Commit', icon: '🚀' },
    { id: 'rollback', label: 'Rollback', icon: '⏮️' }
];

const MetamorphosisChamber = ({
    isOpen,
    onClose,
    modelPath,
    onEvolutionComplete
}) => {
    // State
    const [currentStage, setCurrentStage] = useState('propose');
    const [telemetry, setTelemetry] = useState(null);
    const [simulationResults, setSimulationResults] = useState(null);
    const [tensorDiff, setTensorDiff] = useState(null);
    const [isAuthorized, setIsAuthorized] = useState(false);
    
    // Refs
    const chamberRef = useRef(null);
    const workerRef = useRef(null);
    
    useEffect(() => {
        // Initialize WebWorker for simulation
        workerRef.current = new Worker('/evolution-worker.js');
        workerRef.current.onmessage = handleWorkerMessage;
        
        // Start telemetry updates
        const telemetryInterval = setInterval(updateTelemetry, 1000);
        
        return () => {
            workerRef.current?.terminate();
            clearInterval(telemetryInterval);
        };
    }, []);
    
    const updateTelemetry = async () => {
        try {
            const response = await fetch('/api/evolution/telemetry');
            const data = await response.json();
            setTelemetry(data);
        } catch (err) {
            console.error('Failed to update telemetry:', err);
        }
    };
    
    const handleWorkerMessage = (event) => {
        const { type, data } = event.data;
        switch (type) {
            case 'simulation_complete':
                setSimulationResults(data);
                break;
            case 'tensor_diff':
                setTensorDiff(data);
                break;
            default:
                console.warn('Unknown worker message:', type);
        }
    };
    
    const handleStageTransition = async (stage) => {
        setCurrentStage(stage);
        
        switch (stage) {
            case 'simulate':
                workerRef.current.postMessage({
                    type: 'start_simulation',
                    modelPath
                });
                break;
                
            case 'validate':
                // Trigger validation checks
                break;
                
            case 'commit':
                if (!isAuthorized) {
                    alert('Operator authorization required');
                    return;
                }
                try {
                    const response = await fetch('/api/evolution/commit', {
                        method: 'POST',
                        body: JSON.stringify({ modelPath })
                    });
                    if (response.ok) {
                        onEvolutionComplete();
                    }
                } catch (err) {
                    console.error('Failed to commit evolution:', err);
                }
                break;
                
            case 'rollback':
                // Trigger rollback protocol
                break;
        }
    };
    
    const handleVoiceConfirmation = (confirmed) => {
        setIsAuthorized(confirmed);
    };
    
    return (
        <Modal
            open={isOpen}
            onClose={onClose}
            aria-labelledby="metamorphosis-chamber"
        >
            <Box sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '90vw',
                height: '90vh',
                bgcolor: 'background.paper',
                boxShadow: 24,
                p: 4,
                borderRadius: 2
            }}>
                <Typography variant="h4" component="h2" gutterBottom>
                    🦋 ASTRA Evolution Modal v2 — "Metamorphosis Chamber"
                </Typography>
                
                <Grid container spacing={3}>
                    {/* Left Panel - Evolution Timeline */}
                    <Grid item xs={3}>
                        <Paper sx={{ p: 2, height: '100%' }}>
                            <Timeline>
                                {evolutionStages.map((stage, index) => (
                                    <TimelineItem key={stage.id}>
                                        <TimelineSeparator>
                                            <TimelineDot
                                                color={currentStage === stage.id ? 'primary' : 'grey'}
                                            >
                                                {stage.icon}
                                            </TimelineDot>
                                            {index < evolutionStages.length - 1 && (
                                                <TimelineConnector />
                                            )}
                                        </TimelineSeparator>
                                        <TimelineContent>
                                            <Typography>
                                                {stage.label}
                                            </Typography>
                                        </TimelineContent>
                                    </TimelineItem>
                                ))}
                            </Timeline>
                        </Paper>
                    </Grid>
                    
                    {/* Center Panel - Visualization */}
                    <Grid item xs={6}>
                        <Paper sx={{ p: 2, height: '100%' }}>
                            {currentStage === 'simulate' && (
                                <SimulationPanel
                                    results={simulationResults}
                                />
                            )}
                            {tensorDiff && (
                                <HeatmapVisualizer
                                    data={tensorDiff}
                                />
                            )}
                        </Paper>
                    </Grid>
                    
                    {/* Right Panel - Telemetry & Controls */}
                    <Grid item xs={3}>
                        <Paper sx={{ p: 2, height: '100%' }}>
                            <TelemetryDashboard
                                data={telemetry}
                            />
                            <VoiceConfirmation
                                onConfirmed={handleVoiceConfirmation}
                            />
                            <Button
                                variant="contained"
                                color="primary"
                                fullWidth
                                disabled={!isAuthorized}
                                onClick={() => handleStageTransition('commit')}
                                sx={{ mt: 2 }}
                            >
                                Commit Evolution
                            </Button>
                        </Paper>
                    </Grid>
                </Grid>
            </Box>
        </Modal>
    );
};

export default MetamorphosisChamber;