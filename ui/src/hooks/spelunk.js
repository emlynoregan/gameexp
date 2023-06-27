import React, {useEffect, useState} from 'react';
import { useError } from './error';
// create a useSpelunk hook that can take a url and return the data
// it should be a provider that can be used by the spelunk component

// make a context
const SpelunkContext = React.createContext();

// make a provider
export function SpelunkProvider({ children }) {
    const [spelunkData, setSpelunkData] = useState({});

    const { setError } = useError();

    const api_url = process.env.REACT_APP_API_URL;

    const createSpelunk = async (url, force) => {
        // check if the spelunk already exists
        if (!force && spelunkData[url])
            return;

        const spelunk_api_url = `${api_url}/api/v1/spelunk`;

        const data = {
            url: url
        }

        const response = await fetch(spelunk_api_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.status >= 200 && response.status < 300) {
            const spelunk = await response.json();

            const newSpelunkData = {}
            newSpelunkData[url] = spelunk;

            setSpelunkData((prevSpelunkData) => {
                return {
                    ...prevSpelunkData,
                    ...newSpelunkData
                }
            });
        }
        else {
            setError(`Error creating spelunk (${response.status}): ${response.statusText}`);
        }
    }

    const value = {
        spelunkData,
        createSpelunk
    };

    return <SpelunkContext.Provider value={value}>{children}</SpelunkContext.Provider>;
}

// make a consumer
export function useSpelunk() {
    const context = React.useContext(SpelunkContext);
    if (context === undefined) {
        throw new Error('useSpelunk must be used within a SpelunkProvider');
    }
    return context;
}