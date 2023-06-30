import React, { useState, useRef, useEffect } from 'react';


const GameView = ({ images, sprites, viewCenter, viewWidth, mapTopLeft, mapBottomRight }) => {
/* 
    images is a list of image objects. An image must be suitable for using with the canvas drawImage 
    function. Allowed image types are HTMLImageElement, SVGImageElement, HTMLVideoElement, HTMLCanvasElement, 
    ImageBitmap, OffscreenCanvas, ImageData, or SVGImageElement.
    
    sprites is a list of lists or sprite objects. The lists can in turn be lists or sprite objects, 
    transitively as deep as you like. A sprite object must have the following properties:
        image_index: The index of the image in the images list to draw for this sprite.
        position: An object with x and y properties, giving the position of the sprite in the game world.
        size: The size of the sprite in the game world.
        rotation: The rotation of the sprite in degrees.
    The sprites are drawn in the order they appear in the list, using in-order traversal of inner lists.

    viewCenter and viewWidth are used to synthesise viewTopLeft and viewBottomRight. viewCenter is the center
    of the view in the game world. viewWidth is the width of the view in the game world. We want the game 
    world to show up square on the canvas, so the viewHeight is calculated from the viewWidth and the aspect
    ratio of the canvas. viewTopLeft and viewBottomRight are the top left and bottom right corners of the view01
    viewTopLeft and viewBottomRight can then be calculated from viewCenter and viewWidth, and the aspect ratio.

    mapTopLeft and mapBottomRight are the top left and bottom right corners of the whole map in the game world. We 
    will paint black outside this area.

    Note that all coordinates are Game Coordinates, ie: a self consistent coordinate system that is independent
    
*/
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const animationFrameIdRef = useRef(null);

    const canvas = canvasRef.current;

    const [canvasSize, setCanvasSize] = useState(null);

    useEffect(() => {
        if (canvas && canvasSize) {
            canvas.width = canvasSize.width;
            canvas.height = canvasSize.height;
        }
    }, [canvasSize, canvas]);

    useEffect(() => {
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        const container = containerRef.current;

        const aspectRatio = canvas.height / canvas.width;

        const viewHeight = viewWidth * aspectRatio;

        const viewTopLeft = { x: viewCenter.x - viewWidth / 2, y: viewCenter.y - viewHeight / 2 };
        const viewBottomRight = { x: viewCenter.x + viewWidth / 2, y: viewCenter.y + viewHeight / 2 };

        let resizeTimeout;

        const GameSizeToCanvasSize = canvas.width / (viewBottomRight.x - viewTopLeft.x);

        // Function to update canvas size
        const updateCanvasSize = () => {
            if (resizeTimeout) {
                clearTimeout(resizeTimeout);
            }

            resizeTimeout = setTimeout(() => {
                if (container) {
                    // only do this if the value is changed
                    if (!(canvas.width === container.offsetWidth && canvas.height === container.offsetHeight)) {
                        setCanvasSize({ width: container.offsetWidth, height: container.offsetHeight });
                    }
                }
            }, 100);
        };

        
        const GameXToCanvasX = (gameX) => {
            const canvasX = (gameX - viewTopLeft.x) * GameSizeToCanvasSize;
            return canvasX;
        };

        const GameXSizeToCanvasXSize = (gameXSize) => {
            const canvasXSize = gameXSize * GameSizeToCanvasSize;
            return canvasXSize;
        };

        const GameYToCanvasY = (gameY) => {
            const canvasY = (gameY - viewTopLeft.y) * GameSizeToCanvasSize; // * canvas.height / (viewBottomRight.y - viewTopLeft.y);
            return canvasY;
        };

        const GameYSizeToCanvasYSize = (gameYSize) => {
            const canvasYSize = gameYSize * GameSizeToCanvasSize; //canvas.height / (viewBottomRight.y - viewTopLeft.y);
            return canvasYSize;
        };
        
        const drawBlackBackground = () => {
            context.save();
            
            context.fillStyle = 'black';

            // We need to detect if any of the outside of the map is visible, and if so, draw it black.
            
            // First, if the view is entirely outside the map, then we can just draw the whole canvas black.

            if (viewBottomRight.x < mapTopLeft.x || viewTopLeft.x > mapBottomRight.x || viewBottomRight.y < mapTopLeft.y || viewTopLeft.y > mapBottomRight.y) {
                context.fillRect(0, 0, canvas.width, canvas.height);
            }
            else
            {
                // If the top of the map (mapTopLeft.y) is below the top of the view (viewTopLeft.y), then we need to draw
                // a black rectangle from the top of the view to the top of the map.

                if (mapTopLeft.y > viewTopLeft.y) {
                    const rectLeftCanvas = 0;
                    const rectTopCanvas = 0;
                    const rectWidthCanvas = canvas.width;
                    const rectHeightCanvas = GameYToCanvasY(mapTopLeft.y - viewTopLeft.y);
                    context.fillRect(rectLeftCanvas, rectTopCanvas, rectWidthCanvas, rectHeightCanvas);
                }

                // If the bottom of the map (mapBottomRight.y) is above the bottom of the view (viewBottomRight.y), then we need to draw
                // a black rectangle from the bottom of the map to the bottom of the view.

                if (mapBottomRight.y < viewBottomRight.y) {
                    const rectLeftCanvas = 0;
                    const rectTopCanvas = GameYToCanvasY(mapBottomRight.y);
                    const rectWidthCanvas = canvas.width;
                    const rectHeightCanvas = canvas.height - rectTopCanvas;
                    context.fillRect(rectLeftCanvas, rectTopCanvas, rectWidthCanvas, rectHeightCanvas);
                }

                // If the left of the map (mapTopLeft.x) is to the right of the left of the view (viewTopLeft.x), then we need to draw
                // a black rectangle from the left of the view to the left of the map.

                if (mapTopLeft.x > viewTopLeft.x) {
                    const rectLeftCanvas = 0;
                    const rectTopCanvas = 0;
                    const rectWidthCanvas = GameXToCanvasX(mapTopLeft.x - viewTopLeft.x);
                    const rectHeightCanvas = canvas.height;
                    context.fillRect(rectLeftCanvas, rectTopCanvas, rectWidthCanvas, rectHeightCanvas);
                }

                // If the right of the map (mapBottomRight.x) is to the left of the right of the view (viewBottomRight.x), then we need to draw
                // a black rectangle from the right of the map to the right of the view.

                if (mapBottomRight.x < viewBottomRight.x) {
                    const rectLeftCanvas = GameXToCanvasX(mapBottomRight.x);
                    const rectTopCanvas = 0;
                    const rectWidthCanvas = canvas.width - rectLeftCanvas;
                    const rectHeightCanvas = canvas.height;
                    context.fillRect(rectLeftCanvas, rectTopCanvas, rectWidthCanvas, rectHeightCanvas);
                }
            }

            context.restore();
        };



        // Function to draw sprites on the canvas
        const drawSprites = () => {
            const flattenedSprites = sprites.flat(Infinity);

            flattenedSprites.forEach(sprite => {
                const image = images[sprite.image_index];

                const sprite_width = sprite.sWidth || image.width;
                const sprite_height = sprite.sHeight || image.height;
                const sprite_sx = sprite.sx || 0;
                const sprite_sy = sprite.sy || 0;
                // console.log(image)
                // console.log(sprite);

                // detect if the sprite is outside the view, and if so, don't draw it.

                // console.log(images)

                if (image && !(sprite.position.x + sprite.size < viewTopLeft.x || sprite.position.x > viewBottomRight.x || sprite.position.y + sprite.size < viewTopLeft.y || sprite.position.y > viewBottomRight.y)) {

                    // Save the current state
                    context.save();

                    // // Apply rotation
                    // const centerX = sprite.position.x + sprite.size / 2;
                    // const centerY = sprite.position.y + sprite.size / 2;
                    // context.translate(centerX, centerY);
                    // context.rotate((sprite.rotation * Math.PI) / 180);
                    // context.translate(-centerX, -centerY);

                    // we have two coordinate systems.

                    // The sprites, and the top left and bottom right  are in Game coordinates.
                    // The canvas is in canvas coordinates.

                    // We need to translate the sprite position from Game coordinates to canvas coordinates.

                    const x_window = GameXToCanvasX(sprite.position.x);
                    const y_window = GameYToCanvasY(sprite.position.y);
                    const x_size_window = GameXSizeToCanvasXSize(sprite.size);
                    const y_size_window = GameYSizeToCanvasYSize(sprite.size);
                    
                    // Draw image
                    context.drawImage(
                        image,
                        sprite_sx,
                        sprite_sy,
                        sprite_width,
                        sprite_height,
                        x_window,
                        y_window,
                        x_size_window+1,
                        y_size_window+1
                    );

                    // Restore to the state
                    context.restore();
                }
            });
        };

        // Function to update the content of the canvas
        const updateContent = () => {
            // Clear the entire canvas
            context.clearRect(0, 0, canvas.width, canvas.height);

            // Draw a black background
            drawBlackBackground();

            // Draw sprites
            drawSprites();

            // Draw a black border around the canvas
            context.strokeStyle = 'black';
            context.lineWidth = 1;
            context.strokeRect(0, 0, canvas.width, canvas.height);

            // Request the next animation frame
            animationFrameIdRef.current = requestAnimationFrame(updateContent);
        };

        // Initial update of canvas size
        updateCanvasSize();

        // Start the animation loop
        animationFrameIdRef.current = requestAnimationFrame(updateContent);

        // Watch for container resize and update canvas size
        const resizeObserver = new ResizeObserver(updateCanvasSize);
        resizeObserver.observe(container);

        // Cleanup
        return () => {
            resizeObserver.disconnect();
            cancelAnimationFrame(animationFrameIdRef.current);
            clearTimeout(resizeTimeout);
        };

    }, [images, sprites, viewCenter, viewWidth, mapTopLeft, mapBottomRight, canvasSize]);

    return (
        <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
            <canvas ref={canvasRef} style={{ display: 'block' }} />
        </div>
    );
};

export {GameView};
