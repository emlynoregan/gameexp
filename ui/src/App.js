// import './App.css';
import Router from './routes.js';
import { BrowserRouter } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { createTheme } from '@mui/material/styles';
import { ThemeProvider } from '@emotion/react';
// import grey
import { grey, purple, green } from '@mui/material/colors';
import { ErrorProvider } from './hooks/error';
import { SpelunkProvider } from './hooks/spelunk';

// primary color should be purple
// secondary color should be green

const basePalette = {
  primary: {
    main: purple[500],
    light: purple[300],
    dark: purple[700],
  },
  secondary: {
    main: green[500],
    light: green[300],
    dark: green[700],
  },
}

const lightPalette = {
  ...basePalette,
  mode: 'light',
  background: {
    default: grey[100],
    paper: grey[200],
  }
}

const darkPalette = {
  ...basePalette,
  mode: 'dark',
  background: {
    default: grey[900],
    paper: grey[800],
  }
}

const theme = createTheme({
  palette: lightPalette
});

function App() {
  // const theme = useTheme();

  // // change the theme to dark
  // const toggleDarkTheme = () => {
  //   const newPaletteType = theme.palette.mode === 'light' ? 'dark' : 'light';
  //   theme.palette.mode = newPaletteType;
  // };

  // // use a primary color of purple, and a secondary color of green
  // theme.palette.primary.main = '#9c27b0';
  // theme.palette.secondary.main = '#4caf50';

  // // set the background color to black
  // theme.palette.background = '#000';


  // theme.palette.mode = 'dark';


  return (
    <>
      <ThemeProvider theme={theme}>
        <ErrorProvider>
          <SpelunkProvider>
            <CssBaseline />
            <BrowserRouter>
              <Router />
            </BrowserRouter>
          </SpelunkProvider>
        </ErrorProvider>
      </ThemeProvider>
    </>
  );
}

export default App;
