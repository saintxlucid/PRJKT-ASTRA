/**
 * Heatmap Visualization Component
 * ==============================
 * Renders tensor difference heatmaps with interactive layers
 */

import React, { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import * as d3 from 'd3';

const HeatmapVisualizer = ({ data }) => {
    const svgRef = useRef(null);
    
    useEffect(() => {
        if (!data || !svgRef.current) return;
        
        const svg = d3.select(svgRef.current);
        const width = svg.node().getBoundingClientRect().width;
        const height = svg.node().getBoundingClientRect().height;
        
        // Clear previous content
        svg.selectAll("*").remove();
        
        // Create color scale
        const colorScale = d3.scaleSequential(d3.interpolateRdBu)
            .domain([-1, 1]); // Differences range from -1 to 1
            
        // Draw heatmap cells
        const cellSize = Math.min(width, height) / Math.sqrt(data.length);
        
        svg.selectAll("rect")
            .data(data)
            .enter()
            .append("rect")
            .attr("x", (d, i) => (i % Math.sqrt(data.length)) * cellSize)
            .attr("y", (d, i) => Math.floor(i / Math.sqrt(data.length)) * cellSize)
            .attr("width", cellSize)
            .attr("height", cellSize)
            .attr("fill", d => colorScale(d))
            .on("mouseover", (event, d) => {
                // Show tooltip
                const tooltip = svg.append("g")
                    .attr("class", "tooltip");
                    
                tooltip.append("rect")
                    .attr("x", event.pageX - 60)
                    .attr("y", event.pageY - 40)
                    .attr("width", 120)
                    .attr("height", 30)
                    .attr("fill", "white")
                    .attr("stroke", "#ccc");
                    
                tooltip.append("text")
                    .attr("x", event.pageX)
                    .attr("y", event.pageY - 20)
                    .attr("text-anchor", "middle")
                    .text(`Δ = ${d.toFixed(4)}`);
            })
            .on("mouseout", () => {
                svg.selectAll(".tooltip").remove();
            });
            
        // Add legend
        const legend = svg.append("g")
            .attr("transform", `translate(${width - 100}, 20)`);
            
        const legendScale = d3.scaleLinear()
            .domain([-1, 1])
            .range([0, 100]);
            
        const legendAxis = d3.axisRight(legendScale)
            .ticks(5);
            
        legend.append("g")
            .call(legendAxis);
            
        // Add gradient bar
        const gradientData = d3.range(-1, 1.1, 0.1);
        
        legend.selectAll("rect")
            .data(gradientData)
            .enter()
            .append("rect")
            .attr("x", -20)
            .attr("y", d => legendScale(d))
            .attr("width", 20)
            .attr("height", 2)
            .attr("fill", d => colorScale(d));
            
    }, [data]);
    
    if (!data) {
        return (
            <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography>
                    No tensor difference data available
                </Typography>
            </Box>
        );
    }
    
    return (
        <Box sx={{ width: '100%', height: '100%' }}>
            <Typography variant="h6" gutterBottom>
                Tensor Differential Analysis
            </Typography>
            <svg
                ref={svgRef}
                style={{
                    width: '100%',
                    height: 'calc(100% - 40px)',
                    border: '1px solid #ccc',
                    borderRadius: 4
                }}
            />
        </Box>
    );
};

export default HeatmapVisualizer;