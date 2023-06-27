import React from 'react';

// make a context
const ErrorContext = React.createContext();

// make a provider
export function ErrorProvider({ children }) {
    const [error, setError] = React.useState(null);

    const clearError = () => {
        setError(null);
    };

    const value = {
        error,
        setError,
        clearError
    };

    return <ErrorContext.Provider value={value}>{children}</ErrorContext.Provider>;
}

// make a consumer
export function useError() {
    const context = React.useContext(ErrorContext);
    if (context === undefined) {
        throw new Error('useError must be used within a ErrorProvider');
    }
    return context;
}