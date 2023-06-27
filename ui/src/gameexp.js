import React, { useState, useEffect } from 'react';
import { 
    Button, Typography, TextField, Grid, CircularProgress 
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useSpelunk } from './hooks/spelunk';
import { useError } from './hooks/error';
import { GameWindow } from './gamewindow';

export const GameExp = () => {
    return <>
    <img id="image1" src="path/to/your/image1.png" alt="" style={{ display: 'none' }} />
            
        <img id="grass" src="./grass.png" style={{ display: 'none' }} />
        <img id="mountain" src="./mountain.png" style={{ display: 'none' }} />
        <img id="tree" src="./tree.png" style={{ display: 'none' }} />
        <GameExpInner />
    </>
};

const GameExpInner = () => {
    const tree = document.getElementById("tree");
    const grass = document.getElementById("grass");
    const mountain = document.getElementById("mountain");

    const images = [grass, mountain, tree];
    const sprites = [
        {
            image_index: 0,
            position: { x: 0, y: 0 },
            size: 100,
            rotation: 0,
        },
        {
            image_index: 1,
            position: { x: 100, y: 0 },
            size: 100,
            rotation: 0,
        },
        {
            image_index: 2,
            position: { x: 200, y: 0 },
            size: 100,
            rotation: 0,
        },
    ];

    return (
        <>
        <Grid container spacing={2} justifyContent={'center'}>
            <Grid container spacing={2} 
                justifyContent="center" 
                sx = {{padding: 7}}
                maxWidth="lg"
                // direction="column"
                alignItems="center"
            >
                <Grid item xs={12} sx={{ height: '800px' }}>
                    <GameWindow images={images} sprites={sprites} topLeft={{x:50, y:0}} bottomRight={{x:300, y:300}} />
                </Grid>
            </Grid>
        </Grid>
        </>
    );
};