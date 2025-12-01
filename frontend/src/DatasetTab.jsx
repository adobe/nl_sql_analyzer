// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth

import React, { useState, useCallback, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Typography,
  CircularProgress,
  Paper,
  Grid,
  Card,
  CardContent,
  Tooltip,
  IconButton,
  Collapse,
  Button
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';
import {
  CloudUpload,
  CheckCircle,
  Info,
  ExpandMore,
  ExpandLess,
  Refresh,
  AssignmentTurnedIn,
  Category,
  TrendingUp
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#64b5f6',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: "'Roboto', 'Helvetica', 'Arial', sans-serif",
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 4px 20px 0 rgba(0,0,0,0.1)',
          transition: 'box-shadow 0.3s, transform 0.3s',
          '&:hover': {
            boxShadow: '0 8px 30px 0 rgba(0,0,0,0.2)',
            transform: 'translateY(-5px)',
          },
        },
      },
    },
  },
});

const COLORS = ['#3f51b5', '#f50057', '#00bcd4', '#ff9800', '#4caf50', '#9c27b0', '#795548', '#607d8b'];

const SummaryCard = ({ title, value, icon: Icon }) => (
  <Card elevation={3} sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Icon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
        <Typography variant="h6">{title}</Typography>
      </Box>
      <Typography variant="h4" color="secondary.main">{value}</Typography>
    </CardContent>
  </Card>
);

const AnalysisSummary = ({ analysisResult }) => {
  const totalQueries = analysisResult?.totalQueries || 0;
  const uniqueKeywords = analysisResult?.keywordDistribution?.data?.length || 0;
  const averageComplexity = analysisResult?.averageComplexity?.toFixed(2) || 0;

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      <Grid item xs={12} md={4}>
        <SummaryCard title="Total Queries" value={totalQueries} icon={AssignmentTurnedIn} />
      </Grid>
      <Grid item xs={12} md={4}>
        <SummaryCard title="Unique Keywords" value={uniqueKeywords} icon={Category} />
      </Grid>
      <Grid item xs={12} md={4}>
        <SummaryCard title="Average Complexity" value={averageComplexity} icon={TrendingUp} />
      </Grid>
    </Grid>
  );
};

const EnhancedDatasetAnalysisDashboard = ({
  port,
  ip,
  schema,
  file,
  setFile,
  analysisResult,
  setAnalysisResult,
  loading,
  setLoading,
  expandedCards,
  setExpandedCards,
}) => {
  const onDrop = useCallback((acceptedFiles) => {
    setFile(acceptedFiles[0]);
    handleUpload(acceptedFiles[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  const handleUpload = async (uploadFile) => {
    setLoading(true);
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('schema', JSON.stringify(schema));

    try {
      const response = await fetch(`http://${ip}:${port}/analyze_dataset`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setAnalysisResult(result);
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Error uploading file. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleCardExpansion = (cardId) => {
    setExpandedCards(prev => ({ ...prev, [cardId]: !prev[cardId] }));
  };

  const memoizedChartData = useMemo(() => {
    if (!analysisResult) return {};

    const processData = (data, dataKey) =>
      data?.slice(0, 10).map(item => ({
        ...item,
        [dataKey]: typeof item[dataKey] === 'number' ? item[dataKey] : parseFloat(item[dataKey])
      }));

    return {
      keywordDistribution: processData(analysisResult.keywordDistribution?.data, 'count'),
      clauseNumberDistribution: processData(analysisResult.clauseNumberDistribution?.data, 'count'),
      referenceValueDistribution: processData(analysisResult.referenceValueDistribution?.data, 'count'),
      usedColumnsDistribution: processData(analysisResult.usedColumnsDistribution?.data, 'count'),
      usedTablesDistribution: processData(analysisResult.usedTablesDistribution?.data, 'count'),
      queryComplexityDistribution: processData(analysisResult.queryComplexityDistribution?.data, 'count'),
      concreteColumnDistribution: processData(analysisResult.concreteColumnDistribution?.data, 'count'),
      concreteTableDistribution: processData(analysisResult.concreteTableDistribution?.data, 'count'),
      structureDistribution: analysisResult.structureDistribution?.data?.map(item => ({
        ...item,
        value: typeof item.value === 'number' ? item.value : parseFloat(item.value)
      }))
    };
  }, [analysisResult]);

  const renderChart = (chartData, title, dataKey, explanation, examples, cardId, ChartComponent = BarChart) => (
    <Card elevation={3} sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" gutterBottom>{title}</Typography>
          <Box>
            <Tooltip title={explanation}>
              <IconButton size="small">
                <Info />
              </IconButton>
            </Tooltip>
            <IconButton size="small" onClick={() => toggleCardExpansion(cardId)}>
              {expandedCards[cardId] ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>
        </Box>
        <Collapse in={!expandedCards[cardId]}>
          <Box sx={{ height: 200 }}>
            {chartData && chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ChartComponent data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <RechartsTooltip />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {ChartComponent === BarChart ? (
                    <Bar dataKey={dataKey} fill={theme.palette.primary.main} />
                  ) : (
                    <Line type="monotone" dataKey={dataKey} stroke={theme.palette.secondary.main} activeDot={{ r: 6 }} />
                  )}
                </ChartComponent>
              </ResponsiveContainer>
            ) : (
              <Typography>No data available</Typography>
            )}
          </Box>
        </Collapse>
        <Collapse in={expandedCards[cardId]}>
          <Typography variant="subtitle2" gutterBottom>Examples:</Typography>
          <ul>
            {examples && examples.map((example, index) => (
              <li key={index}><Typography variant="body2">{example}</Typography></li>
            ))}
          </ul>
        </Collapse>
      </CardContent>
    </Card>
  );

  const renderPieChart = (chartData, title, explanation, examples, cardId) => (
    <Card elevation={3} sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" gutterBottom>{title}</Typography>
          <Box>
            <Tooltip title={explanation}>
              <IconButton size="small">
                <Info />
              </IconButton>
            </Tooltip>
            <IconButton size="small" onClick={() => toggleCardExpansion(cardId)}>
              {expandedCards[cardId] ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>
        </Box>
        <Collapse in={!expandedCards[cardId]}>
          <Box sx={{ height: 200 }}>
            {chartData && chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={60}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Typography>No data available</Typography>
            )}
          </Box>
        </Collapse>
        <Collapse in={expandedCards[cardId]}>
          <Typography variant="subtitle2" gutterBottom>Examples:</Typography>
          <ul>
            {examples && examples.map((example, index) => (
              <li key={index}><Typography variant="body2">{example}</Typography></li>
            ))}
          </ul>
        </Collapse>
      </CardContent>
    </Card>
  );

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ p: 3, backgroundColor: 'background.default', minHeight: '100vh' }}>
        <Typography variant="h4" gutterBottom sx={{ mb: 4, color: 'text.primary' }}>Dataset Analysis Dashboard</Typography>

        <Paper
          {...getRootProps()}
          sx={{
            p: 5,
            textAlign: 'center',
            cursor: 'pointer',
            backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
            border: `2px dashed ${theme.palette.primary.main}`,
            borderRadius: 2,
            mb: 4,
            transition: 'all 0.3s',
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }}
        >
          <input {...getInputProps()} />
          {loading ? (
            <CircularProgress />
          ) : file ? (
            <Box>
              <CheckCircle sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
              <Typography variant="h6" color="primary">{file.name} uploaded successfully</Typography>
              <Button
                variant="contained"
                color="secondary"
                startIcon={<Refresh />}
                onClick={() => setFile(null)}
                sx={{ mt: 2 }}
              >
                Upload Another File
              </Button>
            </Box>
          ) : (
            <Box>
              <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" color="primary">Drag and drop a JSON file here, or click to select a file</Typography>
            </Box>
          )}
        </Paper>

        {analysisResult && (
          <>
            <AnalysisSummary analysisResult={analysisResult} />
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                {renderPieChart(
                  memoizedChartData.structureDistribution,
                  'SQL Structure Distribution',
                  analysisResult.structureDistribution?.explanation,
                  analysisResult.structureDistribution?.examples,
                  'structureDistribution'
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.keywordDistribution,
                  'Keyword Distribution',
                  'count',
                  analysisResult.keywordDistribution?.explanation,
                  analysisResult.keywordDistribution?.examples,
                  'keywordDistribution'
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.clauseNumberDistribution,
                  'Clause Number Distribution',
                  'count',
                  analysisResult.clauseNumberDistribution?.explanation,
                  analysisResult.clauseNumberDistribution?.examples,
                  'clauseNumberDistribution',
                  LineChart
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.referenceValueDistribution,
                  'Number of Values in SQL',
                  'count',
                  analysisResult.referenceValueDistribution?.explanation,
                  analysisResult.referenceValueDistribution?.examples,
                  'referenceValueDistribution'
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.usedColumnsDistribution,
                  'Number of Columns in SQL',
                  'count',
                  analysisResult.usedColumnsDistribution?.explanation,
                  analysisResult.usedColumnsDistribution?.examples,
                  'usedColumnsDistribution'
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.usedTablesDistribution,
                  'Number of Tables in SQL',
                  'count',
                  analysisResult.usedTablesDistribution?.explanation,
                  analysisResult.usedTablesDistribution?.examples,
                  'usedTablesDistribution'
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.queryComplexityDistribution,
                  'Query Complexity Distribution',
                  'count',
                  analysisResult.queryComplexityDistribution?.explanation,
                  analysisResult.queryComplexityDistribution?.examples,
                  'queryComplexityDistribution',
                  LineChart
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.concreteColumnDistribution,
                  'Column Usage Distribution',
                  'count',
                  analysisResult.concreteColumnDistribution?.explanation,
                  analysisResult.concreteColumnDistribution?.examples,
                  'concreteColumnDistribution'
                )}
              </Grid>
              <Grid item xs={12} md={4}>
                {renderChart(
                  memoizedChartData.concreteTableDistribution,
                  'Table Usage Distribution',
                  'count',
                  analysisResult.concreteTableDistribution?.explanation,
                  analysisResult.concreteTableDistribution?.examples,
                  'concreteTableDistribution'
                )}
              </Grid>
            </Grid>
          </>
        )}
      </Box>
    </ThemeProvider>
  );
};

export default EnhancedDatasetAnalysisDashboard;