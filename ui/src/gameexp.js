import React, { useState, useEffect } from 'react';
import { 
    Button, Typography, TextField, Grid, CircularProgress 
} from '@mui/material';
import { GameView } from './gameview';

export const GameExp = () => {
    const [images, setImages] = useState({});

    const handleLoad = (event) => {
        const image = event.target;

        setImages(prevImages => {
            return {
                ...prevImages,
                [image.id]: image,
            };
        });
    };

    return <>
        <img id="terrain" src="./terrain_tiles_v2.png" style={{ display: 'none' }} onLoad={handleLoad} />
        <img id="char" src="./Character_007.png" style={{ display: 'none' }} onLoad={handleLoad} />
            
        {/* <img id="grass" src="./grass.png" style={{ display: 'none' }} onLoad={handleLoad} />
        <img id="mountain" src="./mountain.png" style={{ display: 'none' }} onLoad={handleLoad} />
        <img id="tree" src="./tree.png" style={{ display: 'none' }} onLoad={handleLoad} /> */}
        <GameExpInner images={images} />
    </>
};

const GameExpInner = ({images}) => {
    const imageList = [images.terrain, images.char];

    // 0 = tree, 1 = grass, 2 = mountain
    // the map is mostly grass, with a few trees and mountains
    const tileIndices = [
        [55, 55, 55, 55, 55, 55, 55, 55, 55, 55], // 0
        [55, 55, 55, 55, 55, 55, 55, 55, 55, 55], // 1
        [55, 55, 55, 55, 55, 55, 55, 55, 55, 55], // 2
        [55, 55, 55, 0, 1, 1, 2, 55, 55, 55], // 3
        [55, 55, 55, 10, 11, 11, 12, 55, 55, 55], // 4
        [55, 55, 55, 10, 11, 11, 12, 55, 55, 55], // 5
        [55, 55, 55, 20, 42, 40, 22, 55, 55, 55], // 6
        [55, 55, 55, 55, 10, 12, 55, 55, 55, 55], // 7
        [55, 55, 55, 55, 10, 12, 55, 55, 55, 55], // 8
        [55, 55, 55, 55, 10, 12, 55, 55, 55, 55]  // 9
    ]

    const [mapTiles, setMapTiles] = useState([]);

    const mapTopLeft = { x: 0, y: 0 };
    const mapBottomRight = { x: 1000, y: 1000 };
    const [viewCenter, setViewCenter] = useState({ x: 500, y: 500 });
    const [viewSize, setViewSize] = useState(1100); 

    const viewTopLeft = {
        x: viewCenter.x - viewSize / 2,
        y: viewCenter.y - viewSize / 2,
    };

    const viewBottomRight = {
        x: viewCenter.x + viewSize / 2,
        y: (viewCenter.y + viewSize / 2)
    };

    useEffect(() => {
        const newMapTiles = [];
        for (let y = 0; y < tileIndices.length; y++) {
            for (let x = 0; x < tileIndices[y].length; x++) {
                const tileNum = tileIndices[y][x];
                // calculate the tile's position in the tileset image
                const sx = ((tileNum % 10) * 32);
                const sy = (Math.floor(tileNum / 10) * 32)+1;

                newMapTiles.push({
                    image_index: 0,
                    position: { x: x * 100, y: y * 100 },
                    size: 100,
                    rotation: 0,
                    sx,
                    sy,
                    sWidth: 30,
                    sHeight: 30
                });
            }
        }
        setMapTiles(newMapTiles);
    }, []);


    // when the user presses the arrow keys, move the view
    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'ArrowLeft') {
                setViewCenter((prevViewCenter) => ({
                    ...prevViewCenter,
                    x: prevViewCenter.x - 10,
                }));
            } else if (event.key === 'ArrowRight') {
                setViewCenter((prevViewCenter) => ({
                    ...prevViewCenter,
                    x: prevViewCenter.x + 10,
                }));
            } else if (event.key === 'ArrowUp') {
                setViewCenter((prevViewCenter) => ({
                    ...prevViewCenter,
                    y: prevViewCenter.y - 10,
                }));
            } else if (event.key === 'ArrowDown') {
                setViewCenter((prevViewCenter) => ({
                    ...prevViewCenter,
                    y: prevViewCenter.y + 10,
                }));
            } else if (event.key === '+') {
                setViewSize((prevViewSize) => prevViewSize - 10);
            } else if (event.key === '-') {
                setViewSize((prevViewSize) => prevViewSize + 10);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, []);

    // now add the character
    // the character is 32x32 pixels, and the tile map is 16 tiles (each 32x32), 4 x 4.

    const [charPosition, setCharPosition] = useState({ x: 500, y: 500 });
    const charSize = 75; // in game units
    const [charDirection, setCharDirection] = useState('down');
    const [charAnimation, setCharAnimation] = useState(0); // 0 to 3
    // recalculate the view center based on the character's position
    // min is left/top, max is right/bottom
    

    useEffect(() => {
        const viewCenterX = Math.max(Math.min(charPosition.x, mapBottomRight.x), mapTopLeft.x); 
        const viewCenterY = Math.max(Math.min(charPosition.y, mapBottomRight.y), mapTopLeft.y);
        setViewCenter({ x: viewCenterX, y: viewCenterY });
        // console.log(viewCenterX, viewCenterY);
    }, [charPosition]);
    

    // drive the character with asdw
    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'a') {
                // check if the character is at the edge of the map
                console.log(charPosition.x, mapTopLeft.x);
                if (charPosition.x > mapTopLeft.x+(charSize/2)) {
                    setCharPosition((prevCharPosition) => ({
                        ...prevCharPosition,
                        x: prevCharPosition.x - 10,
                    }));
                }
                setCharDirection('left');
                setCharAnimation((prevCharAnimation) => (prevCharAnimation + 1) % 4);
            } else if (event.key === 'd') {
                console.log(charPosition.x, mapBottomRight.x);
                if (charPosition.x < mapBottomRight.x-(charSize/2)) {
                    setCharPosition((prevCharPosition) => ({
                        ...prevCharPosition,
                        x: prevCharPosition.x + 10,
                    }));
                }
                setCharDirection('right');
                setCharAnimation((prevCharAnimation) => (prevCharAnimation + 1) % 4);
            } else if (event.key === 'w') {
                if (charPosition.y > mapTopLeft.y+(charSize/2)) {
                    setCharPosition((prevCharPosition) => ({
                        ...prevCharPosition,
                        y: prevCharPosition.y - 10,
                    }));
                }
                setCharDirection('up');
                setCharAnimation((prevCharAnimation) => (prevCharAnimation + 1) % 4);
            } else if (event.key === 's') {
                if (charPosition.y < mapBottomRight.y-(charSize/2)) {
                    setCharPosition((prevCharPosition) => ({
                        ...prevCharPosition,
                        y: prevCharPosition.y + 10,
                    }));
                }
                setCharDirection('down');
                setCharAnimation((prevCharAnimation) => (prevCharAnimation + 1) % 4);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [charPosition]);

    const [charTiles, setCharTiles] = useState([]);

    useEffect(() => {
        // calculate the tile's position in the tileset image
        const row = charDirection === 'down' ? 0 : charDirection === 'left' ? 1 : charDirection === 'right' ? 2 : 3;
        const column = charAnimation;

        const sx = (column * 48);
        const sy = (row * 48)+1;
        const sWidth = 48;
        const sHeight = 48;

        setCharTiles([{
            image_index: 1,
            position: { x: charPosition.x - charSize/2, y: charPosition.y - charSize/2 },
            size: charSize,
            rotation: 0,
            sx,
            sy,
            sWidth,
            sHeight
        }]);
    }, [charPosition, charDirection, charAnimation]);

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
                    <Grid item xs={6} sx={{ height: '500px'}}>
                        <GameView
                            images={imageList} 
                            sprites={[mapTiles, charTiles]}
                            viewTopLeft={viewTopLeft}
                            viewBottomRight={viewBottomRight}
                            mapTopLeft={mapTopLeft}
                            mapBottomRight={mapBottomRight}
                        />
                    </Grid>
                </Grid>
            </Grid>
        </>
    );
};