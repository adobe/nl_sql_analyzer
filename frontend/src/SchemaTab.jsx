// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth

import React, { useCallback, useState, useRef, useMemo, useEffect } from 'react';
import ReactFlow, {
    MiniMap,
    Controls,
    Background,
    addEdge,
    NodeToolbar,
    Handle,
    Position,
    ReactFlowProvider,
    MarkerType,
    applyNodeChanges,
    applyEdgeChanges
} from 'reactflow';

import 'reactflow/dist/style.css';
import { Button, Checkbox, FormControlLabel, Snackbar, IconButton } from '@mui/material';
import Alert from '@mui/material/Alert';
import DeleteIcon from '@mui/icons-material/Delete';


// Constants
const COLUMN_HEIGHT = 25;
const COLUMN_GAP = 5;
const TABLE_HEADER_HEIGHT = 15;
const TABLE_WIDTH = 145;
const COLUMN_WIDTH = 130;

// Style configurations
const EdgeConfig = {
    animated: true,
    type: 'default',
    style: {
        stroke: '#94CAD80',
        strokeWidth: 2
    },
    markerEnd: {
        type: MarkerType.ArrowClosed,
    },
};

const handleStyle = {
    width: 3,
    height: 7,
    background: 'linear-gradient(145deg, #B9E1EC, #9FD4E4)',
    borderRadius: '30%',
    boxShadow: '0px 0px 1px rgba(0,0,0,0.1)',
};

const tableNodeStyle = {
    borderRadius: '10px',
    padding: '10px',
    background: 'white',
    width: `${TABLE_WIDTH}px`,
};

const tableHeaderStyle = {
    fontWeight: '650',
    marginBottom: '10px',
    height: `${TABLE_HEADER_HEIGHT}px`,
    color: '#635D5C',
    fontSize: '14px',
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
};

const columnContainerStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '5px',
};

const columnStyle = {
    padding: '1px',
    border: '1px solid #ddd',
    borderRadius: '10px',
    background: 'white',
    position: 'relative',
    height: `${COLUMN_HEIGHT}px`,
    width: `${COLUMN_WIDTH}px`,
    display: 'flex',
    alignItems: 'center',
    fontSize: '12px',
    margin: 'auto',
};

const commentBoxStyle = {
    position: 'absolute',
    right: '-10px',
    top: '50%',
    transform: 'translate(100%, -50%)',
    background: 'white',
    border: '2px dotted #ddd',
    padding: '3px',
    borderRadius: '3px',
    zIndex: 2000,
    minWidth: '100px',
    maxWidth: '400px',
    width: '150px',
    height: 'auto',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    minHeight: '23px',
};

const commentTextStyle = {
    fontSize: '12px',
    color: "#A9A9A9",
    fontStyle: 'italic',
};

const editableTextStyle = {
    width: '100%',
    minWidth: '20px',
    maxWidth: '125px',
    minHeight: '1em',
    textAlign: 'left',
    cursor: 'text',
    fontSize: '13px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    transition: 'all 0.2s ease',
    padding: '0px',
    margin: '8px',
};

const editableInputStyle = {
    ...editableTextStyle,
    outline: '1px solid #ddd',
    borderRadius: '5px',
    border: 'none',
    background: 'transparent',
    fontSize: '13px',
    width: '90%',
    textAlign: 'center',
    color: '#635D5C',
};

const EditableText = ({ initialValue, onSubmit, style }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [value, setValue] = useState(initialValue);

    const handleClick = () => setIsEditing(true);

    const handleBlur = () => {
        setIsEditing(false);
        onSubmit(value);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleBlur();
        }
    };

    if (isEditing) {
        return (
            <input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                autoFocus
                style={{ ...editableInputStyle, ...style }}
            />
        );
    }

    return (
        <div
            onClick={handleClick}
            style={{ ...editableTextStyle, ...style }}
        >
            {value || '\u00A0'}
        </div>
    );
};

const Comment = ({ comment, onCommentChange }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [value, setValue] = useState(comment);

    const handleClick = () => setIsEditing(true);

    const handleUpdate = () => {
        setIsEditing(false);
        onCommentChange(value);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleUpdate();
        }
    };

    if (isEditing) {
        return (
            <div style={{ display: 'flex', alignItems: 'center' }}>
                <input
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    autoFocus
                    style={{ ...commentTextStyle, width: '80%', marginRight: '5px' }}
                />
                <button
                    onClick={handleUpdate}
                    style={{
                        padding: '4px 8px',
                        background: 'linear-gradient(45deg, #3498db, #2980b9)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '12px',
                        fontSize: '10px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease',
                        boxShadow: '0 2px 5px rgba(52, 152, 219, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}
                    onMouseEnter={(e) => {
                        e.target.style.transform = 'scale(1.05)';
                        e.target.style.boxShadow = '0 4px 8px rgba(52, 152, 219, 0.5)';
                    }}
                    onMouseLeave={(e) => {
                        e.target.style.transform = 'scale(1)';
                        e.target.style.boxShadow = '0 2px 5px rgba(52, 152, 219, 0.3)';
                    }}
                >
                    update
                </button>
            </div>
        );
    }

    return (
        <span onClick={handleClick} style={commentTextStyle}>
            {comment || 'Add description ...'}
        </span>
    );
};

const dataTypes = [
    'text', 'boolean', 'int', 'timestamp', 'float', 'double', 'decimal', 'enum'
];

const TableNode = ({ data, id: nodeId, selected }) => {
    const [hoveredColumn, setHoveredColumn] = useState(null);
    const [isCommentVisible, setIsCommentVisible] = useState(false);
    const [isTableCommentVisible, setIsTableCommentVisible] = useState(false);
    const [isTableHovered, setIsTableHovered] = useState(false);
    const timeoutRef = useRef(null);

    const handleTableMouseEnter = () => {
        setIsTableHovered(true);
    };

    const handleTableMouseLeave = () => {
        setIsTableHovered(false);
        setIsTableCommentVisible(false);
    };

    const handleMouseEnter = (columnId) => {
        setHoveredColumn(columnId);
        setIsCommentVisible(true);
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }
    };

    const handleMouseLeave = () => {
        timeoutRef.current = setTimeout(() => {
            setIsCommentVisible(false);
            setHoveredColumn(null);
        }, 300);
    };

    const handleTableCommentMouseEnter = () => {
        setIsTableCommentVisible(true);
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }
    };

    const handleTableCommentMouseLeave = () => {
        setIsTableCommentVisible(false);
    };

    const nodeStyle = {
        ...tableNodeStyle,
        border: selected ? '1px solid #A4BAB7' : '1px solid #ddd',
        boxShadow: selected ? '0 0 10px rgba(125, 125, 0, 0.5)' : '0 0 5px rgba(125, 125, 125, 0.4)',
    };

    return (
        <div
            style={nodeStyle}
            onMouseEnter={handleTableMouseEnter}
            onMouseLeave={handleTableMouseLeave}
        >
            <div style={{
                ...tableHeaderStyle,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                position: 'relative',
                height: '20px',
            }}
                onMouseEnter={handleTableCommentMouseEnter}
                onMouseLeave={handleTableCommentMouseLeave}
            >
                <div style={{ flex: 1 }}>
                    <EditableText
                        initialValue={data.label}
                        onSubmit={(newValue) => data.onTableNameChange(nodeId, newValue)}
                    />
                </div>
                <div style={{
                    width: '20px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                }}>
                    {isTableHovered && (
                        <div
                            style={{
                                cursor: 'pointer',
                                position: 'relative',
                                padding: '10px',
                                margin: '-10px',
                            }}
                        >
                            {isTableCommentVisible && (
                                <div style={{
                                    ...commentBoxStyle,
                                    position: 'absolute',
                                    top: '-30px',
                                    left: '70%',
                                    transform: 'translateY(5px)',
                                    zIndex: 1000,
                                    minWidth: '150px',
                                    border: '1px solid #ccc',
                                    borderRadius: '20px',
                                    padding: '10px',
                                    backgroundColor: 'lightyellow',
                                }}>
                                    <Comment
                                        comment={data.comment}
                                        onCommentChange={(newComment) => data.onTableCommentChange(nodeId, newComment)}
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div style={columnContainerStyle}>
                {data.columns.map((column, index) => (
                    <div
                        key={column.id}
                        style={{
                            ...columnStyle,
                            display: 'flex',
                            alignItems: 'center',
                            padding: '0 5px',
                            background: column.data.isPrimary ? '#e6f7ff' : 'white',
                        }}
                        onMouseEnter={() => handleMouseEnter(column.id)}
                        onMouseLeave={handleMouseLeave}
                    >
                        <Handle
                            type="target"
                            position={Position.Left}
                            id={`${column.id}-left`}
                            style={{ ...handleStyle, left: -4 }}
                        />
                        {hoveredColumn === column.id && (
                            <div style={{ position: 'absolute', left: '-95px', zIndex: 10 }}>
                                <DataTypeSelector
                                    dataType={column.data.dataType}
                                    onDataTypeChange={(newDataType) => data.onColumnDataTypeChange(nodeId, column.id, newDataType)}
                                />
                            </div>
                        )}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            width: '100%',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                                {column.data.isPrimary && (
                                    <span style={{ marginRight: '5px', color: '#1890ff', fontWeight: 'bold' }}>PK</span>
                                )}
                                <EditableText
                                    initialValue={column.data.label}
                                    onSubmit={(newValue) => data.onColumnNameChange(nodeId, column.id, newValue)}
                                    style={{ flex: 1 }}
                                />
                            </div>
                            {hoveredColumn === column.id && (
                                <IconButton
                                    size="small"
                                    onClick={() => data.onRemoveColumn(nodeId, column.id)}
                                    style={{
                                        padding: '2px',
                                        marginLeft: '2px',
                                        color: '#ff4d4f',
                                        transition: 'all 0.3s',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.transform = 'scale(1.1)';
                                        e.currentTarget.style.color = '#ff1f1f';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.transform = 'scale(1)';
                                        e.currentTarget.style.color = '#ff4d4f';
                                    }}
                                >
                                    <DeleteIcon style={{ fontSize: '16px' }} />
                                </IconButton>
                            )}
                        </div>
                        <Handle
                            type="source"
                            position={Position.Right}
                            id={`${column.id}-right`}
                            style={{ ...handleStyle, right: -4 }}
                        />
                        {hoveredColumn === column.id && isCommentVisible && (
                            <div
                                style={{
                                    ...commentBoxStyle,
                                    position: 'absolute',
                                    left: '105%',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    zIndex: 1000,
                                }}
                                onMouseEnter={() => {
                                    if (timeoutRef.current) {
                                        clearTimeout(timeoutRef.current);
                                    }
                                }}
                                onMouseLeave={handleMouseLeave}
                            >
                                <Comment
                                    comment={column.data.comment}
                                    onCommentChange={(newComment) => data.onColumnCommentChange(nodeId, column.id, newComment)}
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

const DataTypeSelector = ({ dataType, onDataTypeChange }) => {
    return (
        <select
            value={dataType}
            onChange={(e) => onDataTypeChange(e.target.value)}
            style={{
                fontSize: '10px',
                padding: '2px 4px',
                border: '1px solid #ccc',
                borderRadius: '3px',
                background: 'linear-gradient(to bottom, #ffffff, #f9f9f9)',
                color: '#333',
                cursor: 'pointer',
                width: '90px',
                outline: 'none',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
                transition: 'all 0.2s ease-in-out',
            }}
        >
            {dataTypes.map((type) => (
                <option key={type} value={type} >
                    {type}
                </option>
            ))}
        </select>
    );
};

function useRemoveAttribution() {
    useEffect(() => {
        const removeAttribution = () => {
            const attribution = document.querySelector('.react-flow__attribution');
            if (attribution) {
                attribution.style.visibility = 'hidden';
            }
        };

        removeAttribution();

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    removeAttribution();
                }
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });

        return () => observer.disconnect();
    }, []);
}

let id = 1000;
const getId = () => `${id++}`;

function TableNodeWithToolBar({ id, data, onAddColumn, onRemoveColumn, selected }) {
    const [newColumnName, setNewColumnName] = useState('');
    const [isPrimaryKey, setIsPrimaryKey] = useState(false);

    const handleAddColumn = () => {
        if (newColumnName) {
            onAddColumn(id, newColumnName, isPrimaryKey);
            setNewColumnName('');
            setIsPrimaryKey(false);
        }
    };

    const handleInputChange = (e) => {
        setNewColumnName(e.target.value);
    };

    return (
        <>
            <NodeToolbar isVisible={data.toolbarVisible} position={data.toolbarPosition} align="start">
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '2%',
                    padding: '10px',
                    background: 'linear-gradient(45deg, #fff3f3, #ffffff)',
                    borderRadius: '25px',
                    boxShadow: '0 4px 15px rgba(0, 0, 0, 0.1)'
                }}>
                    <input
                        type="text"
                        placeholder="Add new column"
                        value={newColumnName}
                        onChange={handleInputChange}
                        style={{
                            display: 'flex',
                            padding: '12px 15px',
                            border: '2px solid #3498db',
                            borderRadius: '25px',
                            fontSize: '16px',
                            outline: 'none',
                            transition: 'all 0.3s ease',
                            width: '60%',
                            boxShadow: '0 2px 5px rgba(52, 152, 219, 0.2)',
                        }}
                    />
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={isPrimaryKey}
                                onChange={(e) => setIsPrimaryKey(e.target.checked)}
                                color="primary"
                                size="small"
                            />
                        }
                        label="PK"
                        style={{ padding: '1px 2px 1px 3px', marginRight: '2px' }}
                    />
                    <button
                        onClick={handleAddColumn}
                        style={{
                            padding: '5px 5px 5px 5px',
                            display: 'flex',
                            background: 'linear-gradient(45deg, #3498db, #2980b9)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '55px',
                            fontSize: '24px',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                            transition: 'all 0.3s ease',
                            boxShadow: '0 4px 10px rgba(52, 152, 219, 0.3)',
                        }}
                    >
                        &nbsp;+&nbsp;
                    </button>
                </div>
            </NodeToolbar>

            <div style={{ height: '7px' }} />
            <TableNode
                id={id}
                data={{
                    ...data,
                    onRemoveColumn: onRemoveColumn
                }}
                selected={selected}
            />
        </>
    );
}
function SchemaTab(props) {
    const {
        schema,
        setSchema,
        // showSchemaGraph,
        // setShowSchemaGraph,
        reactFlowInstance,
        setReactFlowInstance,
        graphNodes,
        setGraphNodes,
        graphEdges,
        setGraphEdges,
        // fetchSchema,
        updateSchema,
        shouldRender,
        setShouldRender,
    } = props;

    const [tempNewSchema, setTempNewSchema] = useState({});
    const [shouldUpdateSchema, setShouldUpdateSchema] = useState(true);
    const [snackbarOpen, setSnackbarOpen] = useState(false);
    const [snackbarMessage, setSnackbarMessage] = useState('');
    const [snackbarSeverity, setSnackbarSeverity] = useState('success');

    const [isAddTableDialogOpen, setIsAddTableDialogOpen] = useState(false);
    const [newTableName, setNewTableName] = useState('');
    const [lastTablePosition, setLastTablePosition] = useState({ x: 50, y: 50 });

    const reactFlowWrapper = useRef(null);
    const fileInputRef = useRef(null);

    const parseGraphToSchema = useCallback((nodes, edges) => {
        const schema = {};
        nodes.forEach((node) => {
            if (node.type === 'tableNode') {
                const tableName = node.data.label;
                schema[tableName] = {
                    comment: node.data.comment || '',
                    columns: node.data.columns.map((column) => ({
                        field: column.data.label,
                        column_description: column.data.comment || '',
                        type: column.data.dataType,
                        isPrimary: column.data.isPrimary || false,
                        foreign_ref: null,
                    }))
                };
            }
        });

        edges.forEach((edge) => {
            const sourceNode = nodes.find(node => node.id === edge.source);
            const targetNode = nodes.find(node => node.id === edge.target);
            if (sourceNode && targetNode) {
                const sourceColumn = sourceNode.data.columns.find(col => `${col.id}-right` === edge.sourceHandle);
                const targetColumn = targetNode.data.columns.find(col => `${col.id}-left` === edge.targetHandle);
                if (sourceColumn && targetColumn) {
                    const sourceTable = sourceNode.data.label;
                    const sourceField = sourceColumn.data.label;
                    const targetTable = targetNode.data.label;
                    const targetField = targetColumn.data.label;
                    schema[targetTable].columns.find(col => col.field === targetField).foreign_ref = `${sourceTable}(${sourceField})`;
                }
            }
        });

        return schema;
    }, []);

    const handleFileDrop = useCallback((event) => {
        event.preventDefault();
        event.stopPropagation();

        const file = event.dataTransfer.files[0];
        if (file && file.type === "application/json") {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const uploadedSchema = JSON.parse(e.target.result);
                    console.log('Uploaded schema:', uploadedSchema);
                    const transformedSchema = transformSchema(uploadedSchema);
                    console.log('Transformed schema:', transformedSchema);
                    setSchema(transformedSchema);
                    setShouldUpdateSchema(true);
                    setShouldRender(true);
                    setSnackbarMessage('Schema uploaded and updated successfully');
                    setSnackbarSeverity('success');
                } catch (error) {
                    console.error('Error parsing uploaded schema:', error);
                    setSnackbarMessage('Error uploading schema. Please check the file format.');
                    setSnackbarSeverity('error');
                }
                setSnackbarOpen(true);
            };
            reader.readAsText(file);
        } else {
            setSnackbarMessage('Please drop a valid JSON file.');
            setSnackbarSeverity('error');
            setSnackbarOpen(true);
        }
    }, [setSchema, setShouldUpdateSchema, setShouldRender]);

    const handleDragOver = useCallback((event) => {
        event.preventDefault();
        event.stopPropagation();
    }, []);

    useEffect(() => {
        const wrapper = reactFlowWrapper.current;
        wrapper.addEventListener('drop', handleFileDrop);
        wrapper.addEventListener('dragover', handleDragOver);

        return () => {
            wrapper.removeEventListener('drop', handleFileDrop);
            wrapper.removeEventListener('dragover', handleDragOver);
        };
    }, [handleFileDrop, handleDragOver]);

    useEffect(() => {
        const newSchema = parseGraphToSchema(graphNodes, graphEdges);
        setTempNewSchema(newSchema);
    }, [graphNodes, graphEdges, parseGraphToSchema]);

    useEffect(() => {
        if (shouldUpdateSchema) {
            updateSchema();
            setShouldUpdateSchema(false);
        }
    }, [schema, shouldUpdateSchema, updateSchema]);

    useEffect(() => {
        if (shouldRender && schema) {
            renderSchemaGraph();
            setShouldRender(false);
        }
    }, [shouldRender, schema]);

    const handleCloseSnackbar = (event, reason) => {
        if (reason === 'clickaway') {
            return;
        }
        setSnackbarOpen(false);
    };

    const handleTableNameChange = useCallback((nodeId, newName) => {
        setGraphNodes((nds) =>
            nds.map((node) =>
                node.id === nodeId ? { ...node, data: { ...node.data, label: newName } } : node
            )
        );
    }, [setGraphNodes]);

    const handleColumnNameChange = useCallback((nodeId, columnId, newName) => {
        setGraphNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    const updatedColumns = node.data.columns.map((col) =>
                        col.id === columnId ? { ...col, data: { ...col.data, label: newName } } : col
                    );
                    return { ...node, data: { ...node.data, columns: updatedColumns } };
                }
                return node;
            })
        );
    }, [setGraphNodes]);

    const handleColumnCommentChange = useCallback((nodeId, columnId, newComment) => {
        setGraphNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    const updatedColumns = node.data.columns.map((col) =>
                        col.id === columnId ? { ...col, data: { ...col.data, comment: newComment } } : col
                    );
                    return { ...node, data: { ...node.data, columns: updatedColumns } };
                }
                return node;
            })
        );
    }, [setGraphNodes]);

    const handleColumnDataTypeChange = useCallback((nodeId, columnId, newDataType) => {
        setGraphNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    const updatedColumns = node.data.columns.map((col) =>
                        col.id === columnId ? { ...col, data: { ...col.data, dataType: newDataType } } : col
                    );
                    return { ...node, data: { ...node.data, columns: updatedColumns } };
                }
                return node;
            })
        );
    }, [setGraphNodes]);

    const handleColumnPrimaryKeyChange = useCallback((nodeId, columnId, isPrimary) => {
        setGraphNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    const updatedColumns = node.data.columns.map((col) =>
                        col.id === columnId ? { ...col, data: { ...col.data, isPrimary } } : col
                    );
                    return { ...node, data: { ...node.data, columns: updatedColumns } };
                }
                return node;
            })
        );
    }, [setGraphNodes]);

    const handleTableCommentChange = useCallback((nodeId, newComment) => {
        setGraphNodes((nds) =>
            nds.map((node) =>
                node.id === nodeId ? { ...node, data: { ...node.data, comment: newComment } } : node
            )
        );
    }, [setGraphNodes]);

    const handleAddColumn = useCallback((parentId, columnName, isPrimaryKey) => {
        const columnId = getId();
        setGraphNodes((nds) => {
            const parentNode = nds.find(node => node.id === parentId);
            if (!parentNode) return nds;

            const columnNode = {
                id: columnId,
                data: {
                    label: columnName,
                    comment: '',
                    dataType: 'text',
                    isPrimary: isPrimaryKey
                },
            };

            const updatedParentNode = {
                ...parentNode,
                data: {
                    ...parentNode.data,
                    columns: [...parentNode.data.columns, columnNode],
                },
                style: {
                    ...parentNode.style,
                    height: TABLE_HEADER_HEIGHT + (parentNode.data.columns.length + 1) * (COLUMN_HEIGHT + COLUMN_GAP),
                },
            };

            return nds.map(node => node.id === parentId ? updatedParentNode : node);
        });
    }, [setGraphNodes]);

    const handleRemoveColumn = useCallback((nodeId, columnId) => {
        setGraphNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    const updatedColumns = node.data.columns.filter((col) => col.id !== columnId);
                    return {
                        ...node,
                        data: {
                            ...node.data,
                            columns: updatedColumns,
                        },
                        style: {
                            ...node.style,
                            height: TABLE_HEADER_HEIGHT + updatedColumns.length * (COLUMN_HEIGHT + COLUMN_GAP),
                        },
                    };
                }
                return node;
            })
        );
        // Remove any edges connected to this column
        setGraphEdges((eds) =>
            eds.filter((edge) =>
                !(edge.source === nodeId && edge.sourceHandle === `${columnId}-right`) &&
                !(edge.target === nodeId && edge.targetHandle === `${columnId}-left`)
            )
        );
    }, [setGraphNodes, setGraphEdges]);


    const handleAddTableClick = () => {
        setIsAddTableDialogOpen(true);
    };

    const handleCloseDialog = () => {
        setIsAddTableDialogOpen(false);
        setNewTableName('');
    };

    const handleAddTable = useCallback(() => {
        const position = reactFlowInstance.project({
            x: Math.random() * 500,
            y: Math.random() * 500,
        });

        const newNode = {
            id: getId(),
            type: 'tableNode',
            position,
            data: {
                label: `Table ${getId()}`,
                comment: '',
                columns: [],
                onTableNameChange: handleTableNameChange,
                onColumnNameChange: handleColumnNameChange,
                onColumnCommentChange: handleColumnCommentChange,
                onColumnDataTypeChange: handleColumnDataTypeChange,
                onColumnPrimaryKeyChange: handleColumnPrimaryKeyChange,
                onTableCommentChange: handleTableCommentChange,
                onRemoveColumn: handleRemoveColumn,
            },
            style: { width: TABLE_WIDTH }
        };

        setGraphNodes((nds) => nds.concat(newNode));
    }, [reactFlowInstance, handleTableNameChange, handleColumnNameChange, handleColumnCommentChange, handleColumnDataTypeChange, handleColumnPrimaryKeyChange, handleTableCommentChange, handleRemoveColumn]);



    const onNodesChange = useCallback(
        (changes) => setGraphNodes((nds) => applyNodeChanges(changes, nds)),
        [setGraphNodes]
    );

    const onEdgesChange = useCallback(
        (changes) => setGraphEdges((eds) => applyEdgeChanges(changes, eds)),
        [setGraphEdges]
    );

    const onConnect = useCallback(
        (params) => {
            setGraphEdges((eds) => addEdge({ ...params, ...EdgeConfig }, eds));
        },
        [setGraphEdges]
    );

    const onDragOver = useCallback((event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event) => {
            event.preventDefault();

            const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
            const type = event.dataTransfer.getData('application/reactflow');

            if (typeof type === 'undefined' || !type) {
                return;
            }

            const position = reactFlowInstance.project({
                x: event.clientX - reactFlowBounds.left,
                y: event.clientY - reactFlowBounds.top,
            });
            const newNode = {
                id: getId(),
                type,
                position,
                data: {
                    label: `Table ${getId()}`,
                    comment: '',
                    columns: [],
                    onTableNameChange: handleTableNameChange,
                    onColumnNameChange: handleColumnNameChange,
                    onColumnCommentChange: handleColumnCommentChange,
                    onColumnDataTypeChange: handleColumnDataTypeChange,
                    onColumnPrimaryKeyChange: handleColumnPrimaryKeyChange,
                    onTableCommentChange: handleTableCommentChange,
                    onRemoveColumn: handleRemoveColumn,
                },
                style: { width: TABLE_WIDTH }
            };

            handleAddTable(newNode);
        },
        [reactFlowInstance, handleTableNameChange, handleColumnNameChange, handleColumnCommentChange, handleColumnDataTypeChange, handleColumnPrimaryKeyChange, handleTableCommentChange, handleRemoveColumn, handleAddTable]
    );

    const nodeTypes = useMemo(() => ({
        tableNode: (props) => (
            <TableNodeWithToolBar
                {...props}
                onAddColumn={handleAddColumn}
                onRemoveColumn={handleRemoveColumn}
            />
        ),
    }), [handleAddColumn, handleRemoveColumn]);

    const onDragStart = (event, nodeType) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

    const renderSchemaGraph = useCallback(() => {
        if (schema) {
            console.log('there is a schema');
            const nodes = [];
            const edges = [];
            const baseXSpacing = TABLE_WIDTH * 2;
            const baseYSpacing = 450;
            const tablesPerColumn = 3;

            // Analyze relationships and score tables
            const tableScores = {};
            Object.entries(schema).forEach(([tableName, tableData]) => {
                let outgoingEdges = 0;
                let incomingEdges = 0;

                if (Array.isArray(tableData)) {
                    tableData.forEach(column => {
                        if (column.foreign_ref) outgoingEdges++;
                    });
                } else if (tableData.columns) {
                    tableData.columns.forEach(column => {
                        if (column.foreign_ref) outgoingEdges++;
                    });
                }

                Object.values(schema).forEach(otherTableData => {
                    if (Array.isArray(otherTableData)) {
                        otherTableData.forEach(column => {
                            if (column.foreign_ref && column.foreign_ref.startsWith(tableName)) incomingEdges++;
                        });
                    } else if (otherTableData.columns) {
                        otherTableData.columns.forEach(column => {
                            if (column.foreign_ref && column.foreign_ref.startsWith(tableName)) incomingEdges++;
                        });
                    }
                });

                tableScores[tableName] = incomingEdges - outgoingEdges;
            });

            // Sort tables based on scores (descending order of score)
            const sortedTables = Object.keys(schema).sort((a, b) => tableScores[b] - tableScores[a]);

            let currentX = 0;
            let currentY = 0;
            let maxHeightInColumn = 0;

            sortedTables.forEach((tableName, index) => {
                const tableData = schema[tableName];
                console.log('tableData:', tableData);

                let columns = [];
                let comment = '';

                if (Array.isArray(tableData)) {
                    columns = tableData;
                } else {
                    columns = tableData.columns || [];
                    comment = tableData.comment || '';
                }

                const nodeHeight = TABLE_HEADER_HEIGHT + columns.length * (COLUMN_HEIGHT + COLUMN_GAP);

                // Adjust spacing based on number of columns
                const xSpacing = baseXSpacing + (columns.length * 10);
                const ySpacing = baseYSpacing + (columns.length * 15);

                if (index % tablesPerColumn === 0 && index !== 0) {
                    currentX += xSpacing;
                    currentY = 0;
                    maxHeightInColumn = 0;
                }

                // Add some randomness to make it look more natural
                const randX = (Math.random() - 0.5) * (xSpacing * 0.3);
                const randY = (Math.random() - 0.5) * (ySpacing * 0.1);

                console.log('(' * 50);
                console.log('tableData:', tableData);
                console.log('(' * 50);

                const tableNode = {
                    id: tableName,
                    type: 'tableNode',
                    position: {
                        x: currentX + randX,
                        y: currentY + randY + ySpacing * 0.3,
                    },
                    data: {
                        label: tableName,
                        comment: tableData[0].table_description || '',
                        columns: columns.map((column) => ({
                            id: `${tableName}-${column.field}`,
                            data: {
                                label: column.field,
                                comment: column.column_description || '',
                                dataType: column.type,
                                isPrimary: column.isPrimary || false,
                                foreign_ref: column.foreign_ref || null,
                            },
                        })),
                        onTableNameChange: handleTableNameChange,
                        onColumnNameChange: handleColumnNameChange,
                        onColumnCommentChange: handleColumnCommentChange,
                        onColumnDataTypeChange: handleColumnDataTypeChange,
                        onColumnPrimaryKeyChange: handleColumnPrimaryKeyChange,
                        onTableCommentChange: handleTableCommentChange,
                        // Remove this line: onRemoveColumn: handleRemoveColumn,
                    },
                    style: { width: TABLE_WIDTH, height: nodeHeight }
                };

                nodes.push(tableNode);

                columns.forEach((column) => {
                    if (column.foreign_ref) {
                        const [refTable, refColumn] = column.foreign_ref.split('(');
                        edges.push({
                            id: `${refTable}-${refColumn.slice(0, -1)}-${tableName}-${column.field}`,
                            source: refTable,
                            target: tableName,
                            sourceHandle: `${refTable}-${refColumn.slice(0, -1)}-right`,
                            targetHandle: `${tableName}-${column.field}-left`,
                            ...EdgeConfig,
                        });
                    }
                });

                currentY += ySpacing;
                maxHeightInColumn = Math.max(maxHeightInColumn, nodeHeight);
            });

            setGraphNodes(nodes);
            setGraphEdges(edges);

            // Set the ReactFlow viewport to show all nodes
            if (reactFlowInstance) {
                setTimeout(() => {
                    reactFlowInstance.fitView({ padding: 0.2 });
                }, 50);
            }
        }
    }, [schema, handleTableNameChange, handleColumnNameChange, handleColumnCommentChange, handleColumnDataTypeChange, handleColumnPrimaryKeyChange, handleTableCommentChange, handleRemoveColumn, setGraphNodes, setGraphEdges, reactFlowInstance]);

    const handleDownloadSchema = async () => {
        try {
            // First, update the schema
            console.log('Updating schema with:', tempNewSchema);
            setSchema(tempNewSchema);
            await updateSchema(); // Assuming updateSchema is an async function

            // Now proceed with the download
            const updatedSchema = JSON.stringify(tempNewSchema, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(updatedSchema);
            const exportFileDefaultName = 'schema.json';

            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();

            setSnackbarMessage('Schema updated and downloaded successfully');
            setSnackbarSeverity('success');
            setSnackbarOpen(true);
        } catch (error) {
            console.error('Error updating or downloading schema:', error);
            setSnackbarMessage('Error updating or downloading schema');
            setSnackbarSeverity('error');
            setSnackbarOpen(true);
        }
    };

    const handleUploadSchema = (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const uploadedSchema = JSON.parse(e.target.result);
                    console.log('Uploaded schema====================:', uploadedSchema);
                    const transformedSchema = transformSchema(uploadedSchema);
                    console.log('Transformed schema====================', transformedSchema);
                    setSchema(transformedSchema);
                    setShouldUpdateSchema(true);
                    setShouldRender(true);
                    setSnackbarMessage('Schema uploaded and updated successfully');
                    setSnackbarSeverity('success');
                } catch (error) {
                    console.error('Error parsing uploaded schema:', error);
                    setSnackbarMessage('Error uploading schema. Please check the file format.');
                    setSnackbarSeverity('error');
                }
                setSnackbarOpen(true);
            };
            reader.readAsText(file);
        }
    };

    function transformSchema(inputSchema) {
        const result = {};

        Object.entries(inputSchema).forEach(([tableName, tableData]) => {
            const { comment, columns } = tableData;
            result[tableName] =
                columns.map(column => ({
                    field: column.field,
                    column_description: column.column_description,
                    type: column.type,
                    isPrimary: column.isPrimary,
                    foreign_ref: column.foreign_ref,
                    table_description: comment // Add the table description to each column
                }))
        });

        return result;
    }

    useRemoveAttribution();

    return (
        <div style={{
            display: 'flex',
            width: '100%',
            height: 'calc(100vh - 81px)',
            padding: '20px',
            backgroundColor: '#f0f0f0',
            gap: '20px',
            boxSizing: 'border-box',
            overflow: 'hidden',
            borderRadius: '15px',
        }}>
            <div style={{
                flex: 1,
                borderRadius: '15px',
                overflow: 'hidden',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
                backgroundColor: 'white'
            }}>
                <ReactFlowProvider>
                    <div style={{ width: '100%', height: '100%' }} ref={reactFlowWrapper}>
                        <ReactFlow
                            nodes={graphNodes}
                            edges={graphEdges}
                            nodeTypes={nodeTypes}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            onInit={setReactFlowInstance}
                            fitView
                        >
                            <Controls
                                position="bottom-left"
                                style={{ left: 10, bottom: 10 }}
                            />
                            <MiniMap
                                position="bottom-right"
                                style={{ right: 10, bottom: 10 }}
                            />
                            <Background
                                variant="dots"
                                gap={15}
                                size={1}
                            />

                            <div style={{
                                position: 'absolute',
                                left: '20px',
                                top: '25px',
                                zIndex: 400
                            }}>
                                <div
                                    onClick={handleAddTable}
                                    style={{
                                        padding: '15px 20px',
                                        border: '3px solid #A898DA',
                                        borderRadius: '15px',
                                        background: 'linear-gradient(45deg, #f3f3f3, #ffffff)',
                                        cursor: 'pointer',
                                        boxShadow: '0 4px 8px rgba(0, 255, 0, 0.3)',
                                        fontFamily: 'Arial, sans-serif',
                                        fontWeight: 'bold',
                                        color: '#333',
                                        fontSize: '16px',
                                        textTransform: 'uppercase',
                                        letterSpacing: '1px',
                                        transition: 'all 0.3s ease',
                                    }}
                                    onMouseEnter={(e) => e.target.style.transform = 'scale(1.05)'}
                                    onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                                >
                                    Add New Table
                                </div>
                            </div>
                        </ReactFlow>
                    </div>
                </ReactFlowProvider>
            </div>

            <div style={{
                width: '110px',
                backgroundColor: 'white',
                padding: '15px',
                display: 'flex',
                flexDirection: 'column',
                gap: '20px',
                borderRadius: '15px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
                overflowY: 'auto'
            }}>
                <Button
                    onClick={async () => {
                        setGraphNodes([]);
                        setGraphEdges([]);
                        setShouldRender(false);
                    }}
                    variant='contained'
                    color='error'
                    size="small"
                >
                    Remove
                </Button>

                {/* <Button
                    onClick={async () => {
                        await fetchSchema();
                        setShouldRender(true);
                    }}
                    variant='contained'
                    color='inherit'
                    size="small"
                    style={{ fontSize: '0.8rem' }}
                >
                    Load AEP
                </Button> */}

                <Button
                    onClick={handleDownloadSchema}
                    variant='contained'
                    color='inherit'
                    size="small"
                >
                    Download
                </Button>

                <Button
                    onClick={() => fileInputRef.current.click()}
                    variant='contained'
                    color='inherit'
                    size="small"
                >
                    Upload
                </Button>

                <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    onChange={handleUploadSchema}
                    accept=".json"
                />

                <Button
                    onClick={() => {
                        console.log('Updating schema with:', tempNewSchema);
                        setShouldRender(false);
                        setSchema(tempNewSchema);
                        setShouldUpdateSchema(true);
                        setSnackbarMessage('Schema updated successfully');
                        setSnackbarSeverity('success');
                        setSnackbarOpen(true);
                    }}
                    variant='contained'
                    color='primary'
                    size="small"
                >
                    Update
                </Button>
            </div>

            <Snackbar
                open={snackbarOpen}
                autoHideDuration={2000}
                onClose={() => setSnackbarOpen(false)}
            >
                <Alert
                    severity={snackbarSeverity}
                    variant="filled"
                    sx={{ width: '100%' }}
                >
                    {snackbarMessage}
                </Alert>
            </Snackbar>
        </div>
    );
}

export default SchemaTab;