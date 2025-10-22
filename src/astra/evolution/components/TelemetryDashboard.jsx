/**
 * Telemetry Dashboard Component
 * ===========================
 * Displays real-time evolution metrics
 */

import React from 'react';
import {
    Box,
    Typography,
    CircularProgress,
    LinearProgress,
    Grid,
    Paper
} from '@mui/material';

const TelemetryDashboard = ({ data }) => {
    if (!data) {
        return (
            <Box sx={{ p: 2, textAlign: 'center' }}>
                <CircularProgress />
                <Typography sx={{ mt: 1 }}>
                    Loading telemetry...
                </Typography>
            </Box>
        );
    }
    
    const {
        cpu_load,
        memory_used,
        evolution_progress,
        entropy_score,
        status
    } = data;
    
    const getStatusColor = () => {
        switch (status) {
            case '🟢':
                return '#4caf50';
            case '🟡':
                return '#ff9800';
            case '🔴':
                return '#f44336';
            default:
                return '#9e9e9e';
        }
    };
    
    const getEntropyColor = (score) => {
        if (score < 0.3) return '#4caf50';
        if (score < 0.75) return '#ff9800';
        return '#f44336';
    };
    
    return (
        <Box>
            <Typography variant="h6" gutterBottom>
                Evolution Telemetry
            </Typography>
            
            {/* Status Ring */}
            <Box
                sx={{
                    position: 'relative',
                    width: 120,
                    height: 120,
                    margin: '0 auto 20px'
                }}
            >
                <Box
                    sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: `4px solid ${getStatusColor()}`,
                        borderRadius: '50%'
                    }}
                >
                    <Typography variant="h4">
                        {status}
                    </Typography>
                </Box>
            </Box>
            
            <Grid container spacing={2}>
                {/* CPU Load */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            CPU Load
                        </Typography>
                        <LinearProgress
                            variant="determinate"
                            value={cpu_load}
                            sx={{ mt: 1, mb: 0.5 }}
                        />
                        <Typography variant="body2" align="right">
                            {cpu_load.toFixed(1)}%
                        </Typography>
                    </Paper>
                </Grid>
                
                {/* Memory Usage */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Memory Usage
                        </Typography>
                        <LinearProgress
                            variant="determinate"
                            value={memory_used}
                            sx={{ mt: 1, mb: 0.5 }}
                        />
                        <Typography variant="body2" align="right">
                            {memory_used.toFixed(1)}%
                        </Typography>
                    </Paper>
                </Grid>
                
                {/* Evolution Progress */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Evolution Progress
                        </Typography>
                        <LinearProgress
                            variant="determinate"
                            value={evolution_progress * 100}
                            sx={{ mt: 1, mb: 0.5 }}
                        />
                        <Typography variant="body2" align="right">
                            {(evolution_progress * 100).toFixed(1)}%
                        </Typography>
                    </Paper>
                </Grid>
                
                {/* Entropy Score */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Entropy Score
                        </Typography>
                        <Box sx={{ 
                            height: 24,
                            bgcolor: getEntropyColor(entropy_score),
                            borderRadius: 1,
                            mt: 1,
                            mb: 0.5,
                            transition: 'background-color 0.3s'
                        }} />
                        <Typography variant="body2" align="right">
                            {entropy_score.toFixed(3)}
                        </Typography>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
};

export default TelemetryDashboard;