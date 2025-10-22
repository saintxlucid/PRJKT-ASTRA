/**
 * Visual Components for Evolution Monitoring
 * =======================================
 * - Live telemetry bar
 * - Model delta heatmap
 * - Risk visualization
 */

import React, { useEffect, useRef, useState } from 'react';
import {
    Box,
    Typography,
    LinearProgress,
    Paper,
    Grid
} from '@mui/material';
import * as d3 from 'd3';

export const TelemetryBar = ({ data }) => {
    if (!data) return null;
    
    const {
        entropy_score,
        severity_score,
        risk_score,
        domain_risks
    } = data;
    
    const getStatusColor = (value) => {
        if (value < 0.3) return '#4caf50';
        if (value < 0.75) return '#ff9800';
        return '#f44336';
    };
    
    return (
        <Box sx={{ width: '100%', p: 1 }}>
            <Grid container spacing={2} alignItems="center">
                {/* Entropy Meter */}
                <Grid item xs={4}>
                    <Typography variant="caption">
                        Entropy: {(entropy_score * 100).toFixed(1)}%
                    </Typography>
                    <LinearProgress
                        variant="determinate"
                        value={entropy_score * 100}
                        sx={{
                            height: 8,
                            backgroundColor: '#e0e0e0',
                            '& .MuiLinearProgress-bar': {
                                backgroundColor: getStatusColor(entropy_score)
                            }
                        }}
                    />
                </Grid>
                
                {/* Severity Meter */}
                <Grid item xs={4}>
                    <Typography variant="caption">
                        Severity: {(severity_score * 100).toFixed(1)}%
                    </Typography>
                    <LinearProgress
                        variant="determinate"
                        value={severity_score * 100}
                        sx={{
                            height: 8,
                            backgroundColor: '#e0e0e0',
                            '& .MuiLinearProgress-bar': {
                                backgroundColor: getStatusColor(severity_score)
                            }
                        }}
                    />
                </Grid>
                
                {/* Risk Score */}
                <Grid item xs={4}>
                    <Typography variant="caption">
                        Risk: {(risk_score * 100).toFixed(1)}%
                    </Typography>
                    <LinearProgress
                        variant="determinate"
                        value={risk_score * 100}
                        sx={{
                            height: 8,
                            backgroundColor: '#e0e0e0',
                            '& .MuiLinearProgress-bar': {
                                backgroundColor: getStatusColor(risk_score)
                            }
                        }}
                    />
                </Grid>
            </Grid>
            
            {/* Domain Risk Indicators */}
            <Box sx={{ mt: 1 }}>
                <Grid container spacing={1}>
                    {Object.entries(domain_risks).map(([domain, risk]) => (
                        <Grid item key={domain}>
                            <Paper
                                sx={{
                                    p: 0.5,
                                    bgcolor: getStatusColor(risk),
                                    color: 'white',
                                    fontSize: '0.75rem'
                                }}
                            >
                                {domain}
                            </Paper>
                        </Grid>
                    ))}
                </Grid>
            </Box>
        </Box>
    );
};

export const ModelDeltaHeatmap = ({ data, width = 800, height = 400 }) => {
    const svgRef = useRef(null);
    
    useEffect(() => {
        if (!data || !svgRef.current) return;
        
        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();
        
        // Set up scales
        const xScale = d3.scaleBand()
            .domain(d3.range(data[0].length))
            .range([0, width])
            .padding(0.1);
            
        const yScale = d3.scaleBand()
            .domain(d3.range(data.length))
            .range([0, height])
            .padding(0.1);
            
        // Color scale for delta values
        const colorScale = d3.scaleSequential(d3.interpolateRdBu)
            .domain([-1, 1]); // Differences range from -1 to 1
            
        // Create heatmap cells
        svg.selectAll("g")
            .data(data)
            .enter()
            .append("g")
            .attr("transform", (d, i) => `translate(0,${yScale(i)})`)
            .selectAll("rect")
            .data(d => d)
            .enter()
            .append("rect")
            .attr("x", (d, i) => xScale(i))
            .attr("width", xScale.bandwidth())
            .attr("height", yScale.bandwidth())
            .attr("fill", d => colorScale(d))
            .on("mouseover", (event, d) => {
                // Show tooltip
                const tooltip = svg.append("g")
                    .attr("class", "tooltip");
                    
                const [x, y] = d3.pointer(event);
                
                tooltip.append("rect")
                    .attr("x", x - 40)
                    .attr("y", y - 30)
                    .attr("width", 80)
                    .attr("height", 20)
                    .attr("fill", "white")
                    .attr("stroke", "#ccc");
                    
                tooltip.append("text")
                    .attr("x", x)
                    .attr("y", y - 15)
                    .attr("text-anchor", "middle")
                    .text(`Δ = ${d.toFixed(4)}`);
            })
            .on("mouseout", () => {
                svg.selectAll(".tooltip").remove();
            });
            
        // Add color scale legend
        const legendWidth = 20;
        const legendHeight = height;
        
        const legendScale = d3.scaleLinear()
            .domain([-1, 1])
            .range([legendHeight, 0]);
            
        const legend = svg.append("g")
            .attr("transform", `translate(${width + 10}, 0)`);
            
        const legendAxis = d3.axisRight(legendScale)
            .ticks(5)
            .tickFormat(d => d.toFixed(1));
            
        legend.append("g")
            .call(legendAxis);
            
        const gradientData = d3.range(-1, 1.1, 0.1);
        
        legend.selectAll("rect")
            .data(gradientData)
            .enter()
            .append("rect")
            .attr("x", 0)
            .attr("y", d => legendScale(d))
            .attr("width", legendWidth)
            .attr("height", legendHeight / gradientData.length)
            .attr("fill", d => colorScale(d));
            
    }, [data, width, height]);
    
    if (!data) {
        return (
            <Typography variant="body2" color="text.secondary">
                No delta data available
            </Typography>
        );
    }
    
    return (
        <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
            <svg
                ref={svgRef}
                style={{
                    width: '100%',
                    height: '100%',
                    overflow: 'visible'
                }}
                viewBox={`0 0 ${width + 50} ${height}`}
            />
        </Box>
    );
};