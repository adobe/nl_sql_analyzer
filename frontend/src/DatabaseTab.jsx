// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth

import React, { useEffect } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Button, MenuItem, Select, Box } from '@mui/material';

function DatabaseTab(props) {
    const {
        currentTable,
        setCurrentTable,
        records,
        schema,
        dbLoading,
        error,
        quantity,
        loading,
        handleSynthesizeRecords,
        fetchSchema,
        fetchRecords,
        saveRecords,
        handleNumChange,
    } = props;

    useEffect(() => {
        console.log('loaded schema', schema);
    }, []);

    return (
        <div style={{ display: 'flex', justifyContent: 'center', width: '100%', padding: '20px 0' }}>
            <div style={{ height: 600, width: '80%' }}> {/* Increased height to accommodate more rows */}
                {Object.keys(schema).length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                            <Button onClick={fetchRecords} disabled={dbLoading} style={{ marginRight: '20px' }}>Load Records</Button>
                            <Button onClick={saveRecords} disabled={dbLoading} style={{ marginRight: '20px' }}>Save Records</Button>
                            <Box style={{ border: '0.5px dotted gray', padding: '10px' }}>
                                <Button variant="contained" color="inherit" onClick={handleSynthesizeRecords} disabled={loading}>Synthesize</Button>
                                <input value={quantity} onChange={handleNumChange} type="number" id="quantity" name="quantity" min="1" max="10000" style={{ width: '50px', marginLeft: '20px' }} />
                            </Box>
                        </div>

                        <Select
                            value={currentTable}
                            onChange={e => setCurrentTable(e.target.value)}
                            displayEmpty
                            inputProps={{ 'aria-label': 'Without label' }}
                            style={{ width: '15%' }}
                        >
                            {Object.keys(schema).map(tableName => (
                                <MenuItem key={tableName} value={tableName}>{tableName}</MenuItem>
                            ))}
                        </Select>
                    </div>
                )}
                {error && <p style={{ color: 'red' }}>{error}</p>}
                {schema[currentTable] && (
                    <DataGrid
                        rows={records[currentTable] || []}
                        columns={schema[currentTable] || []}
                        pageSize={30} // Increased from 5 to 10
                        rowsPerPageOptions={[10, 25, 50, 100]} // Updated options
                        getRowId={(row) => row.id}
                        style={{ border: '2px solid #ccc' }}
                    />
                )}
            </div>
        </div>
    );
};

export default DatabaseTab;