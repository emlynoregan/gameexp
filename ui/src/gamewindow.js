import React, { useRef, useEffect } from 'react';

const GameWindow = ({ images, sprites, topLeft, bottomRight }) => {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const animationFrameIdRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        const container = containerRef.current;

        let resizeTimeout;

        // Function to update canvas size
        const updateCanvasSize = () => {
            if (resizeTimeout) {
                clearTimeout(resizeTimeout);
            }

            resizeTimeout = setTimeout(() => {
                if (container) {
                    canvas.width = container.offsetWidth;
                    canvas.height = container.offsetHeight;
                }
            }, 100);
        };

        // Function to draw sprites on the canvas
        const drawSprites = () => {
            sprites.forEach(sprite => {
                const image = images[sprite.image_index];

                // Save the current state
                context.save();

                // // Apply rotation
                // const centerX = sprite.position.x + sprite.size / 2;
                // const centerY = sprite.position.y + sprite.size / 2;
                // context.translate(centerX, centerY);
                // context.rotate((sprite.rotation * Math.PI) / 180);
                // context.translate(-centerX, -centerY);

                // we have two coordinate systems.

                // The sprites, and the top left and bottom right  are in Sprite coordinates.
                // The canvas is in window coordinates.

                // We need to translate the sprite coordinates to window coordinates.

                const x_mult_sprite_to_window = (bottomRight.x - topLeft.x) / (canvas.width);
                const y_mult_sprite_to_window = (bottomRight.y - topLeft.y) / (canvas.height);

                const x_window = (sprite.position.x - topLeft.x) / x_mult_sprite_to_window;
                const y_window = (sprite.position.y - topLeft.y) / y_mult_sprite_to_window;

                const x_size_window = sprite.size / x_mult_sprite_to_window;
                const y_size_window = sprite.size / y_mult_sprite_to_window;
                
                // Draw image
                context.drawImage(
                    image,
                    x_window,
                    y_window,
                    x_size_window,
                    y_size_window
                );

                

                // Restore to the state
                context.restore();
            });
        };

        // Function to update the content of the canvas
        const updateContent = () => {
            // Clear the entire canvas
            context.clearRect(0, 0, canvas.width, canvas.height);

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

    }, [images, sprites]);

    return (
        <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
            <canvas ref={canvasRef} style={{ display: 'block' }} />
        </div>
    );
};

export {GameWindow};
