import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles/tokens.css';
import './styles/typography.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Fatal: #root mount element missing from index.html');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
