import React, {useEffect, useState} from 'react';
import {Outlet, useRoutes} from 'react-router-dom';
import { GameExp } from './gameexp';

const Layout = () => {
  return (
    <Outlet />
    // <>
    //   {/* <CssBaseline />    
    //   <div>
    //     <h1>Layout</h1>
    //     <Outlet />
    //   </div> */}
    // </>
  );
};
     
export default function Router({targetUrl}) {

  console.log("targetUrl: " + targetUrl);

  const [rerouteTo, setRerouteTo] = useState(null);
  console.log("rerouteTo: " + rerouteTo);

  useEffect(() => {
    if (targetUrl && !rerouteTo)
    {
      setRerouteTo(targetUrl);
    }
  }, [targetUrl, rerouteTo]);

  return useRoutes([
    {
      path: '',
      element: (
        <Layout />
      ),
      children: [
        { path: '', element: <GameExp /> },
        // { path: 'spelunk/:url', element: <Spelunk /> },
      ],
    },
    // { path: '*', element: <Navigate to={"/in/home"} replace /> },
  ]);
}

