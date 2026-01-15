import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Landing from './pages/Landing'
import Apply from './pages/Apply'
import Results from './pages/Results'
import Track from './pages/Track'
import DSA from './pages/DSA'
import Admin from './pages/Admin'

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Layout />}>
                    <Route index element={<Landing />} />
                    <Route path="apply" element={<Apply />} />
                    <Route path="results/:id" element={<Results />} />
                    <Route path="track/:id" element={<Track />} />
                    <Route path="dsa" element={<DSA />} />
                    <Route path="dsa/*" element={<DSA />} />
                    <Route path="admin" element={<Admin />} />
                    <Route path="admin/*" element={<Admin />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
