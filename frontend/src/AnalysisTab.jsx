// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  TextField,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Divider,
  Typography,
  Box,
  CircularProgress,
  Switch,
  FormControlLabel,
  Modal,
  Tooltip,
  Snackbar,
  Paper,
  InputBase,
  LinearProgress,
  Alert
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import ClearIcon from '@mui/icons-material/Clear';
import DownloadIcon from '@mui/icons-material/Download';
import AutoGraphIcon from '@mui/icons-material/AutoGraph';
import { styled } from '@mui/material/styles';
import { DataGrid } from '@mui/x-data-grid';
import { HighlightWithinTextarea } from 'react-highlight-within-textarea';
// import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

import SQLExplanationAndCorrespondence from './SQLSubexpressionCorrespondence';


const FancyHighlight = ({ children }) => (
  <span className="fancy-highlight">{children}</span>
);


const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  backgroundColor: '#ffffff',
  borderRadius: theme.shape.borderRadius,
  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
  border: '1px solid #e0e0e0',
  position: 'relative',
  overflow: 'hidden',
  transition: 'box-shadow 0.3s ease-in-out',
  '&:hover': {
    boxShadow: '0 6px 25px rgba(0, 0, 0, 0.15)',
  },
}));

const StyledInputBase = styled(InputBase)(({ theme }) => ({
  fontFamily: '"Roboto Mono", monospace',
  fontSize: '14px',
  color: '#333333',
  width: '100%',
  height: '200px', // Fixed height
  overflowY: 'auto',
  padding: theme.spacing(1),
  paddingRight: '100px', // Make room for the button
  '& .MuiInputBase-input': {
    padding: 0,
    height: '100%', // Make the input take full height
  },
  '&::selection': {
    backgroundColor: 'rgba(0, 123, 255, 0.2)',
  },
}));


// Custom styled components
const FancyButton = styled(Button)(({ theme }) => ({
  background: 'linear-gradient(45deg, #2196F3 30%, #64B5F6 90%)',
  border: 0,
  borderRadius: 10,
  width: '98%',
  boxShadow: '0 3px 5px 2px rgba(33, 150, 243, .3)',
  color: 'white',
  height: 48,
  padding: '0 30px',
  transition: 'all 0.3s',
  '&:hover': {
    background: 'linear-gradient(45deg, #64B5F6 30%, #2196F3 90%)',
    transform: 'scale(1.02)',
  },
}));

const FancyCard = styled(Card)(({ theme }) => ({
  transition: 'all 0.3s',
  '&:hover': {
    transform: 'translateY(-5px)',
    boxShadow: '0 12px 20px rgba(0, 0, 0, 0.1)',
    elevation: 1,
  },
}));



const ExampleList = ({ examples }) => {
  console.log('Examples:');
  console.log(examples);
  
  // Parse examples if it's a string
  const parsedExamples = React.useMemo(() => {
    if (typeof examples === 'string') {
      try {
        return JSON.parse(examples);
      } catch (error) {
        console.error('Failed to parse examples:', error);
        return [];
      }
    }
    return examples;
  }, []);

  // Ensure parsedExamples is an array
  const examplesArray = Array.isArray(parsedExamples) ? parsedExamples : [parsedExamples];

  if (examplesArray.length === 0) {
    return <Typography>No examples available.</Typography>;
  }

  return (
    <Box sx={{ maxWidth: 800, margin: 'auto', padding: 3 }}>
      <Typography variant="h4" gutterBottom>
        Similar Examples (TOP {examplesArray.length})
      </Typography>
      <Grid container spacing={3}>
        {examplesArray.map((example, index) => (
          <Grid item xs={12} key={index}>
            <Card elevation={3}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
                  Example {index + 1}
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography
                  variant="body2"
                  sx={{
                    backgroundColor: '#f5f5f5',
                    p: 1,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all'
                  }}
                >
                  {example.sql_query}
                </Typography>

                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" paragraph>
                  {example.nl_query}
                </Typography>

                <Divider sx={{ my: 2 }} />

                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography variant="subtitle1" sx={{ mr: 1 }}>
                    Similarity Score:
                  </Typography>
                  <Chip
                    label={Number(example.similarity).toFixed(4)}
                    color="primary"
                    variant="outlined"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

// New component for the schema popup
function SchemaPopup({ open, handleClose, tempSchema, setTempSchema }) {
  return (
    <Modal
      open={open}
      onClose={handleClose}
      aria-labelledby="schema-popup"
      aria-describedby="schema-popup-description"
    >
      <Box sx={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 400,
        bgcolor: 'background.paper',
        border: '2px solid #000',
        boxShadow: 24,
        p: 4,
      }}>
        <Typography id="schema-popup" variant="h6" component="h2" gutterBottom>
          Edit Schema (Optional)
        </Typography>
        <TextField
          label="Enter Schema"
          multiline
          rows={8}
          value={tempSchema}
          onChange={(e) => setTempSchema(e.target.value)}
          variant="outlined"
          fullWidth
        />
        <Button onClick={handleClose} sx={{ mt: 2 }}>Close</Button>
      </Box>
    </Modal>
  );
}













function AnalysisTab(props) {
  const {
    sqlQuery,
    setSqlQuery,
    nlQuery,
    setNlQuery,
    nlQuery_synthesized,
    setNlQuery_synthesized,
    ruleDescription,
    setRuleDescription,
    llmDescription,
    setLLMDescription,
    equivalence,
    setEquivalence,
    score,
    setScore,
    loading_stepBystep,
    loading_analyze,
    setLoading_analyze,
    loading_subQuestions,
    sub_questions,
    setSubQuestions,
    tempSchema,
    setTempSchema,
    useSchema,
    setUseSchema,
    handleStepByStepDescription,
    handleSubQuestions,
    handleAnalyze,
    synthetic_sql,
    setSynthetic_sql,
    loading_synthetic_sql,
    handle_synthetic_sql,
    handleSuggestedNL,
    loading_suggestedNL,
    examples,
    savedData,
    handleAcceptData,
    handleRejectData,
    handleDownloadDataset,
    handleExecuteSQL,
    queryResult,
    setQueryResult,
    parsedData,
    setParsedData,
    handleAnalyzeWithParsing,
    highlightAnalyze,
    setHighlightAnalyze,
    highlightSuggestedNL,
    setHighlightSuggestedNL,
    highlightCheckAlignment,
    setHighlightCheckAlignment,
    highlightRandomSQL,
    setHighlightRandomSQL,
    uncovered_substrings,
    setUncovered_substrings,
    handleInject,
    autoSynthesisCount,
    setAutoSynthesisCount,
    autoSynthesisProgress,
    isAutoSynthesizing,
    startAutoSynthesis,
    stopAutoSynthesis,
    analyzeForAuto,
    setAnalyzeForAuto,
    handleAlertClose,
    alertOpen,
    setAlertOpen,
    alignmentChecked,
    setAlignmentChecked
  } = props;

  const [schemaPopupOpen, setSchemaPopupOpen] = useState(false);
  const [examplesModalOpen, setExamplesModalOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState("");
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);
  const [highlightedSQL, setHighlightedSQL] = useState(null);
  const [highlightSQLRanges, setHighlightSQLRanges] = useState([]);
  const [highlightNLRanges, setHighlightNLRanges] = useState([]);
  const [isHoveringExplanation, setIsHoveringExplanation] = useState(false);
  const [executingSQL, setExecutingSQL] = useState(false);

  const [uncoveredHighlights, setUncoveredHighlights] = useState([]);
  const [hoverHighlights, setHoverHighlights] = useState([]);

  const [inputValue, setInputValue] = useState('');
  const [undoStack, setUndoStack] = useState([]);



  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.ctrlKey && event.key === 'z') {
        event.preventDefault();
        handleUndo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undoStack]);

  useEffect(() => {
    if (highlightedSQL) {
      const start = sqlQuery.indexOf(highlightedSQL);
      if (start !== -1) {
        setHighlightSQLRanges([{
          highlight: [start, start + highlightedSQL.length],
          component: FancyHighlight
        }]);
      }
    } else {
      setHighlightSQLRanges([]);
    }
  }, [highlightedSQL, sqlQuery]);

  useEffect(() => {
    if (uncovered_substrings && uncovered_substrings.length > 0) {
      const validHighlights = uncovered_substrings.filter(substring =>
        nlQuery.includes(substring)
      ).map(substring => ({
        highlight: substring,
        className: 'uncovered-highlight'
      }));
      setUncoveredHighlights(validHighlights);
    } else {
      setUncoveredHighlights([]);
    }
  }, [uncovered_substrings, nlQuery]);



  useEffect(() => {
    // Combine uncovered and hover highlights, prioritizing hover highlights
    const combinedHighlights = [...uncoveredHighlights];

    hoverHighlights.forEach(hoverHighlight => {
      const [start, end] = hoverHighlight.highlight;
      // Remove or adjust any uncovered highlights that overlap with this hover highlight
      for (let i = combinedHighlights.length - 1; i >= 0; i--) {
        const uncoveredHighlight = combinedHighlights[i];
        const uncoveredStart = nlQuery.indexOf(uncoveredHighlight.highlight);
        const uncoveredEnd = uncoveredStart + uncoveredHighlight.highlight.length;

        if (start <= uncoveredStart && end >= uncoveredEnd) {
          // Hover highlight completely covers uncovered highlight, remove it
          combinedHighlights.splice(i, 1);
        } else if (start <= uncoveredStart && end > uncoveredStart) {
          // Partial overlap at the start, adjust uncovered highlight
          const newHighlight = nlQuery.substring(end, uncoveredEnd);
          combinedHighlights[i] = { ...uncoveredHighlight, highlight: newHighlight };
        } else if (start < uncoveredEnd && end >= uncoveredEnd) {
          // Partial overlap at the end, adjust uncovered highlight
          const newHighlight = nlQuery.substring(uncoveredStart, start);
          combinedHighlights[i] = { ...uncoveredHighlight, highlight: newHighlight };
        }
      }
      // Add the hover highlight
      combinedHighlights.push(hoverHighlight);
    });

    setHighlightNLRanges(combinedHighlights);
  }, [hoverHighlights, uncoveredHighlights, nlQuery]);

  const highlightAnimation = {
    animation: 'colorShift 1.5s ease-in-out infinite',
    '@keyframes colorShift': {
      '0%, 100%': {
        backgroundColor: '#2196F3',  // Default blue
        color: 'white',
      },
      '50%': {
        backgroundColor: '#FFF176',  // Light yellow
        color: '#1565C0',  // Dark blue
      },
    },
    transition: 'all 0.3s ease-in-out',
  };



  const handleUndo = () => {
    if (undoStack.length > 0) {
      const previousValue = undoStack[undoStack.length - 1];
      setInputValue(previousValue);
      setUndoStack(prev => prev.slice(0, -1));
    }
  };

  const handleSQLChange = useCallback((value) => {
    setSqlQuery(value);
    setHighlightAnalyze(true);
    setHighlightRandomSQL(false);
    setHighlightSuggestedNL(false);
    setHighlightCheckAlignment(false);
  }, [setSqlQuery, setHighlightAnalyze, setHighlightRandomSQL, setHighlightSuggestedNL, setHighlightCheckAlignment]);

  const handleNLChange = useCallback((value) => {
    setNlQuery(value);
    setHighlightCheckAlignment(true);
    setHighlightRandomSQL(false);
    setHighlightAnalyze(false);
    setHighlightSuggestedNL(false);
    setHighlightNLRanges([]);
  }, [setNlQuery, setHighlightCheckAlignment, setHighlightRandomSQL, setHighlightAnalyze, setHighlightSuggestedNL, setHighlightNLRanges]);

  const getColorForScore = (score) => {
    const hue = 60; // yellow hue
    const saturation = 100;
    const lightness = 100 - (score * 50); // Higher score = lower lightness (brighter color)
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  };

  const handleAnalyzeToggle = () => {
    setAnalyzeForAuto((prev) => !prev);
  };

  const handleHighlightSQL = useCallback((subexpression) => {
    console.log('Highlighting SQL:', subexpression);
    setHighlightedSQL(subexpression);
  }, []);

  const handleHighlightNL = useCallback((alignedEntries) => {
    console.log('Highlighting NL:', alignedEntries);
    if (alignedEntries && alignedEntries.length > 0) {
      const newHighlightRanges = alignedEntries.map(([text, score, className]) => {
        const start = nlQuery.indexOf(text);
        if (start !== -1 && start + text.length <= nlQuery.length) {
          const backgroundColor = getColorForScore(score);
          return {
            highlight: [start, start + text.length],
            className: className || 'fancy-highlight',
            style: { backgroundColor }
          };
        }
        return null;
      }).filter(range => range !== null);

      setHoverHighlights(newHighlightRanges);
      setIsHoveringExplanation(true);
    } else {
      setHoverHighlights([]);
      setIsHoveringExplanation(false);
    }
  }, [nlQuery]);

  const handleOpenSchemaPopup = () => setSchemaPopupOpen(true);
  const handleCloseSchemaPopup = () => setSchemaPopupOpen(false);

  const handleOpenExamplesModal = useCallback(() => {
    setExamplesModalOpen(true);
  }, []);

  const handleCloseExamplesModal = useCallback(() => {
    setExamplesModalOpen(false);
  }, []);
  


  const handleCloseSnackbar = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setSnackbarOpen(false);
  };

  const handleShowResults = async () => {
    try {
      await handleExecuteSQL(sqlQuery);
      setIsResultModalOpen(true);
    } catch (error) {
      console.error("Error executing SQL:", error);
      setSnackbarMessage("Error executing SQL query");
      setSnackbarOpen(true);
    }
  };

  const handleCloseResultModal = () => {
    setIsResultModalOpen(false);
  };

  return (
    <Box sx={{
      display: 'flex',
      gap: 3,
      p: 4,
      background: 'linear-gradient(120deg, #E3F2FD 0%, #DEE4E3 100%)',
      borderRadius: 2,
      minHeight: '100vh',
      border: '1px solid rgba(0,0,0,0.1)',
    }}>
      <Box sx={{ flex: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* <Typography variant="h4" sx={{ color: 'black', textShadow: '2px 2px 4px rgba(0,0,0,0.2)' }}>
          Interactive Dataset Synthesis Dashboard
        </Typography> */}

        <Box display="flex" width="100%" gap="20px">
          <Box sx={{ flex: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* SQL Synthesizer */}
            <FancyCard variant="outlined" sx={{ bgcolor: 'rgba(255,255,255,0.9)' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Typography variant="h6" component="div">&#10102; SQL Query Synthesizer</Typography>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'center', width: '100%', mb: 3 }}>
                  <FancyButton
                    onClick={handle_synthetic_sql}
                    sx={{
                      ...(highlightRandomSQL && highlightAnimation),
                    }}
                  >
                    {loading_synthetic_sql ? <CircularProgress size={24} color="inherit" /> : "Random SQL"}
                  </FancyButton>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'stretch', width: '100%', mb: 2 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleOpenSchemaPopup}
                    sx={{
                      flex: 2,
                      mr: 2,
                      border: '1px solid #1976d2',
                      borderRadius: 2,
                      height: 'auto',
                      alignSelf: 'stretch',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '0px 12px',
                      minWidth: '60px',
                      maxWidth: '90px',
                      fontSize: '0.75rem',
                      color: '#1976d2',
                      '&:hover': {
                        backgroundColor: 'rgba(25, 118, 210, 0.04)',
                      },
                    }}
                  >
                    Edit Schema
                  </Button>

                  <Box sx={{ flexGrow: 1, position: 'relative', flex: 2 }}>
                    <StyledPaper
                      sx={{
                        position: 'relative',
                        height: '125px',
                        overflow: 'hidden',
                        padding: '20px',
                        display: 'flex',
                      }}
                    >
                      <div style={{
                        flexGrow: 1,
                        overflow: 'auto',
                        paddingRight: '100px',
                        scrollbarWidth: 'none',
                        msOverflowStyle: 'none',
                        '&::-webkit-scrollbar': {
                          display: 'none'
                        },
                      }}>
                        <HighlightWithinTextarea
                          value={sqlQuery}
                          highlight={highlightSQLRanges}
                          onChange={handleSQLChange}
                          component={StyledInputBase}
                          placeholder="Input a SQL query..."
                          style={{
                            height: '100%',
                            width: '100%',
                          }}
                        />
                      </div>

                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => {
                          setExecutingSQL(true);
                          handleExecuteSQL(sqlQuery)
                            .then(() => {
                              handleShowResults();
                            })
                            .finally(() => {
                              setExecutingSQL(false);
                            });
                        }}
                        sx={{
                          position: 'absolute',
                          right: '16px',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          zIndex: 1,
                          height: '60%',
                          minWidth: '100px',
                          backgroundColor: '#1976d2',
                          '&:hover': {
                            backgroundColor: '#1565c0',
                          },
                          borderRadius: 3,
                          border: '2px solid white',
                        }}
                      >
                        {executingSQL ? (
                          <CircularProgress size={24} color="inherit" />
                        ) : (
                          "Execute"
                        )}
                      </Button>

                    </StyledPaper>
                  </Box>
                </Box>

                <SchemaPopup
                  open={schemaPopupOpen}
                  handleClose={handleCloseSchemaPopup}
                  tempSchema={tempSchema}
                  setTempSchema={setTempSchema}
                />
              </CardContent>
            </FancyCard>

            {/* Natural Language Synthesizer */}
            <FancyCard variant="outlined" sx={{ bgcolor: 'rgba(255,255,255,0.9)' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Typography variant="h6" component="div">&#10104; Natural Language Synthesizer</Typography>
                </Box>

                <FancyButton
                  onClick={handleSuggestedNL}
                  sx={{
                    ...(highlightSuggestedNL && highlightAnimation),
                  }}
                >
                  {loading_suggestedNL ? <CircularProgress size={24} color="inherit" /> : "Suggested NL Question"}
                </FancyButton>

                <div style={{ height: '30px' }}></div>

                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'stretch', width: '100%', mb: 2 }}>
                  <StyledPaper
                    sx={{
                      position: 'relative',
                      height: '125px',
                      overflow: 'hidden',
                      padding: '20px',
                      display: 'flex',
                      flexGrow: 1,
                      flex: 3,
                    }}
                  >
                    <div style={{
                      flexGrow: 1,
                      overflow: 'auto',
                      msOverflowStyle: 'none',
                      '&::-webkit-scrollbar': {
                        display: 'none'
                      },
                    }}>
                      <HighlightWithinTextarea
                        value={nlQuery}
                        highlight={highlightNLRanges}
                        onChange={handleNLChange}
                        component={StyledInputBase}
                        placeholder="Input a natural language question..."
                        style={{
                          height: '100%',
                          width: '100%',
                        }}
                      />
                    </div>
                  </StyledPaper>

                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleOpenExamplesModal}
                    sx={{
                      ml: 2,
                      flex: 1,
                      border: 'solid',
                      borderRadius: 3,
                      height: 'auto',
                      alignSelf: 'stretch',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '0px 0px',
                      minWidth: '15%',
                      maxWidth: '15%',
                      fontSize: '0.75rem',
                    }}
                  >
                    Similar Examples
                  </Button>
                </Box>

                <div style={{ height: '10px' }}></div>

                <Box sx={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
                  <FancyButton
                    onClick={handleSubQuestions}
                    sx={{
                      ...(highlightCheckAlignment && highlightAnimation),
                    }}
                  >
                    {loading_subQuestions ? <CircularProgress size={24} color="inherit" /> : "Check Alignment"}
                  </FancyButton>
                </Box>
              </CardContent>
            </FancyCard>
          </Box>

          {/* Step-by-Step Analysis */}
          <Box sx={{
            flex: 2,
            bgcolor: 'rgba(255,255,255,0.9)',
            borderRadius: 4,
            display: 'flex',
            flexDirection: 'column',
            p: 2,
          }}>
            <Box display="flex" alignItems="center" mb={2}>
              <Tooltip
                placement='top'
                title="Serves as a reliable contact for translating SQL query to natural language."
                sx={{ ml: 1, cursor: 'help' }}
                arrow
                componentsProps={{
                  tooltip: {
                    sx: {
                      fontSize: '1rem',
                      padding: '8px 12px',
                    }
                  }
                }}
              >
                <Typography variant="h6" component="div">&#10103; Step-by-Step Analysis</Typography>
              </Tooltip>
            </Box>
            <FancyButton
              onClick={handleAnalyzeWithParsing}
              sx={{
                ...(highlightAnalyze && highlightAnimation),
              }}
            >
              {loading_stepBystep ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                "Analyze SQL"
              )}
            </FancyButton>

            {parsedData ? (
              <Box sx={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 300px)' }}>
                <SQLExplanationAndCorrespondence
                  data={parsedData}
                  onHighlightSQL={handleHighlightSQL}
                  onHighlightNL={handleHighlightNL}
                  uncovered_substrings={uncovered_substrings}
                  setUncovered_substrings={setUncovered_substrings}
                  handleInject={handleInject}
                  alignmentChecked={alignmentChecked}
                />
              </Box>
            ) : (
              <Typography variant="body2" color="textSecondary" align="center">
                Click the button above to analyze the SQL query step-by-step.
              </Typography>
            )}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
          <FancyButton onClick={handleAnalyze}>
            {loading_analyze ? <CircularProgress size={24} color="inherit" /> : "Post-Annotation Analysis"}
          </FancyButton>
        </Box>

        <Box display="flex" width="100%" gap="20px">
          <FancyCard variant="outlined" sx={{ flex: 4, bgcolor: 'rgba(255,255,255,0.9)' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Typography variant="h6" component="div">&#10105; Post-Annotation Analysis &nbsp;</Typography>
                <AutoGraphIcon sx={{ mr: 1 }} />
              </Box>

              <TextField
                value={equivalence}
                multiline
                rows={8}
                InputProps={{
                  readOnly: true,
                }}
                variant="outlined"
                fullWidth
                sx={{ backgroundColor: 'rgba(0,0,0,0.025)' }}
              />
            </CardContent>
          </FancyCard>

          <FancyCard sx={{ flex: 1, bgcolor: 'rgba(255,255,255,0.9)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Typography component="div" sx={{ fontSize: '8rem', fontWeight: 'bold', color: '#2196F3' }}>
              {score}
            </Typography>
          </FancyCard>
        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, mt: 0, }}>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', mt: 2 }}>
            <Box sx={{ display: 'flex', gap: 5 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckIcon />}
                onClick={handleAcceptData}
                sx={{ fontSize: '1.2rem', padding: '10px 20px', width: '70%' }}
              >
                Accept
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<ClearIcon />}
                onClick={handleRejectData}
                sx={{ fontSize: '1.2rem', padding: '10px 20px', width: '70%' }}
              >
                Reject
              </Button>
            </Box>

            <FancyCard
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 3,
                border: '1px solid #e0e0e0',
                borderRadius: 2,
                padding: 2,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                width: '60%',
                height: '90px',
              }}
            >
              <Box sx={{ width: '45%', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
                {isAutoSynthesizing ? (
                  <>
                    <LinearProgress
                      variant="determinate"
                      value={(autoSynthesisProgress / autoSynthesisCount) * 100}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 3,
                        },
                      }}
                    />
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, fontSize: '0.75rem' }}>
                      <Typography variant="body2" color="text.secondary">
                        {`${autoSynthesisProgress} / ${autoSynthesisCount}`}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {`${Math.round((autoSynthesisProgress / autoSynthesisCount) * 100)}%`}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 1 }}>
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Synthesizing...
                      </Typography>
                    </Box>
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
                    Click 'Auto Synthesize' to start
                  </Typography>
                )}
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 9, width: '90%' }}>
                <Box sx={{ width: '20%' }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={analyzeForAuto}
                        onChange={handleAnalyzeToggle}
                        color="primary"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ width: '120px', display: 'inline-block' }}>
                        {analyzeForAuto ? 'Post-Analysis: ON' : 'Post-Analysis: OFF'}
                      </Typography>
                    }
                    sx={{ margin: 0 }}
                  />
                </Box>
                <TextField
                  type="number"
                  label="Samples"
                  value={autoSynthesisCount}
                  onChange={(e) => setAutoSynthesisCount(Number(e.target.value))}
                  size="small"
                  sx={{ width: '15%' }}
                  InputLabelProps={{ shrink: true }}
                />
                <FancyButton
                  onClick={() => {
                    if (isAutoSynthesizing) {
                      stopAutoSynthesis();
                    } else {
                      startAutoSynthesis();
                    }
                  }}
                  sx={{
                    width: '30%',
                    height: '40%',
                    fontSize: '1.075rem',
                    backgroundColor: isAutoSynthesizing ? '#f44336' : '#2196F3',
                    '&:hover': {
                      backgroundColor: isAutoSynthesizing ? '#d32f2f' : '#1976D2',
                    },
                    color: 'white',  // Ensure text is always visible
                  }}
                >
                  {isAutoSynthesizing ? 'Stop' : 'Auto Synthesize'}
                </FancyButton>
              </Box>
            </FancyCard>
          </Box>




        </Box>
      </Box>

      {/* Saved Data Card */}
      <FancyCard sx={{ flex: 0.31, height: 'fit-content', position: 'sticky', top: 20 }}>
        <CardContent>
          <Typography sx={{ fontSize: '20px' }} gutterBottom>Saved Data</Typography>
          <Box sx={{ maxHeight: 'calc(90vh - 200px)', minHeight: 'calc(90vh - 200px)', overflowY: 'auto' }}>
            {savedData.map((item, index) => (
              <Tooltip
                placement="left"
                key={index}
                title={
                  <React.Fragment>
                    <Typography color="inherit">SQL: {item.sqlQuery}</Typography>
                    <Typography color="inherit">NL: {item.nlQuery}</Typography>
                    <Typography color="inherit">Score: {item.score}</Typography>
                  </React.Fragment>
                }
                arrow
              >
                <Box sx={{ mb: 1, p: 1, bgcolor: 'rgba(0,0,0,0.05)', borderRadius: 1, cursor: 'pointer' }}>
                  <Typography variant="caption" display="block" noWrap>
                    SQL: {item.sqlQuery.substring(0, 20)}...
                  </Typography>
                  <Typography variant="caption" display="block" noWrap>
                    NL: {item.nlQuery.substring(0, 20)}...
                  </Typography>
                  <Typography variant="caption" display="block">
                    Score: {item.score}
                  </Typography>
                </Box>
              </Tooltip>
            ))}
          </Box>
          <Button
            variant="contained"
            color="primary"
            startIcon={<DownloadIcon />}
            onClick={handleDownloadDataset}
            fullWidth
            sx={{ mt: 2, fontSize: '12.5px' }}
          >
            Download
          </Button>
        </CardContent>
      </FancyCard>

      {/* Modals and Snackbar */}
      <Modal
        open={examplesModalOpen}
        onClose={handleCloseExamplesModal}
        aria-labelledby="examples-modal-title"
        aria-describedby="examples-modal-description"
      >
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '50%',
          maxHeight: '80%',
          bgcolor: 'background.paper',
          border: '2px solid #000',
          boxShadow: 24,
          p: 4,
          overflowY: 'auto',
        }}>
          <ExampleList examples={examples} />
          <Button onClick={handleCloseExamplesModal} sx={{ mt: 2 }}>Close</Button>
        </Box>
      </Modal>

      <Modal
        open={isResultModalOpen}
        onClose={handleCloseResultModal}
        aria-labelledby="query-results-modal"
        aria-describedby="modal-modal-description"
      >
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '80%',
          maxHeight: '80%',
          bgcolor: 'background.paper',
          border: '2px solid #000',
          boxShadow: 24,
          p: 4,
          overflowY: 'auto',
        }}>
          <Typography id="query-results-modal" variant="h6" component="h2" gutterBottom>
            Query Results
          </Typography>
          {queryResult && Object.keys(queryResult).map((tableName) => (
            <Box key={tableName} sx={{ mb: 4 }}>
              <Typography variant="subtitle1" gutterBottom>
                {tableName}
              </Typography>
              <DataGrid
                rows={queryResult[tableName].map((row, index) => ({ ...row, uniqueId: `${tableName}-${index}` }))}
                columns={Object.keys(queryResult[tableName][0] || {}).map(key => ({
                  field: key,
                  headerName: key,
                  flex: 1,
                }))}
                pageSize={5}
                rowsPerPageOptions={[5, 10, 25]}
                autoHeight
                getRowId={(row) => row.uniqueId}
              />
            </Box>
          ))}
          <Button onClick={handleCloseResultModal}>Close</Button>
        </Box>
      </Modal>

      <Snackbar
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        message={snackbarMessage}
      />

      <Snackbar
        open={alertOpen}
        autoHideDuration={4000}
        onClose={handleAlertClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleAlertClose} severity="warning" sx={{ width: '100%' }}>
          Please fill in both SQL and NL queries before accepting.
        </Alert>
      </Snackbar>
    </Box>
  );

}

export default AnalysisTab;