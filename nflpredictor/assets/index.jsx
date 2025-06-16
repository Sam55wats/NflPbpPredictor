import React from 'react'
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import Analysis from './Analysis';

const homeRoot = document.getElementById("root-home");
const analysisRoot = document.getElementById("root-analysis");

if (homeRoot) {
  createRoot(homeRoot).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
}

if (analysisRoot) {
  createRoot(analysisRoot).render(
    <StrictMode>
      <Analysis />
    </StrictMode>
  );
}

/* function App (){
  useEffect(() => {
  fetch("/api/season/")
      .then(response => response.json())
      .then(
        (result) => {
            console.log(result)
        } )
  })
  return <div>Hello World</div>
} 
const root = document.getElementById("root");
console.log(root)
const reactroot = ReactDOM.createRoot(root);
reactroot.render(<App></App>) */
/*window.onload = function() {
  var seasonSelect = document.getElementById("season");
  var gameSelect = document.getElementById("game");
  var teamSelect = document.getElementById("team");

  fetch("/api/seasons/")
    .then(response => response.json())
    .then(
      (result) => {

      }
    )

}*/

