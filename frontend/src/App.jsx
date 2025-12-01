// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth


import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Box, Tabs, Tab, Snackbar, Alert } from '@mui/material';

import { saveAs } from 'file-saver';

import SchemaTab from './SchemaTab';
import DatabaseTab from './DatabaseTab';
import AnalysisTab from './AnalysisTab';
import DatasetTab from './DatasetTab';

import './index.css';

function App() {
  // Main App states
  const port = 5001;
  const ip = 'localhost';

  const [tabValue, setTabValue] = useState(0);

  // Schema Tab states
  const [showSchemaGraph, setShowSchemaGraph] = useState(false);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [shouldRender, setShouldRender] = useState(true);  // used to control whether to render the graph

  // Analysis Tab states
  const [tempSchema, setTempSchema] = useState('N/A');
  const [localSchema, setLocalSchema] = useState('');
  const [sqlQuery, setSqlQuery] = useState('');
  const [nlQuery, setNlQuery] = useState('');
  const [nlQuery_synthesized, setNlQuery_synthesized] = useState('');
  const [ruleDescription, setRuleDescription] = useState('');
  const [llmDescription, setLLMDescription] = useState('');
  const [equivalence, setEquivalence] = useState('');
  const [score, setScore] = useState('');
  const [loading_stepBystep, setLoading_stepBystep] = useState(false);
  const [loading_suggestedNL, setLoading_suggestedNL] = useState(false);
  const [loading_analyze, setLoading_analyze] = useState(false);
  const [loading_subQuestions, setLoading_subQuestions] = useState(false);
  const [sub_questions, setSubQuestions] = useState('');
  const [useSchema, setUseSchema] = useState(false);
  const [synthetic_sql, setSynthetic_sql] = useState('');
  const [loading_synthetic_sql, setLoading_synthetic_sql] = useState(false);
  const [examples, setExamples] = useState([]);
  const [savedData, setSavedData] = useState([]);
  const [queryResult, setQueryResult] = useState('');
  const [parsedData, setParsedData] = useState(null);

  const [autoSynthesisCount, setAutoSynthesisCount] = useState(10);
  const [autoSynthesisProgress, setAutoSynthesisProgress] = useState(0);
  const [isAutoSynthesizing, setIsAutoSynthesizing] = useState(false);
  const synthesisRef = useRef(false);

  const [analyzeForAuto, setAnalyzeForAuto] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);

  const [alignmentChecked, setAlignmentChecked] = useState(false);

  // for prompting operation flow
  const [highlightRandomSQL, setHighlightRandomSQL] = useState(false);
  const [highlightAnalyze, setHighlightAnalyze] = useState(false);
  const [highlightSuggestedNL, setHighlightSuggestedNL] = useState(false);
  const [highlightCheckAlignment, setHighlightCheckAlignment] = useState(false);

  const [uncovered_substrings, setUncovered_substrings] = useState('');

  // Database Tab states
  const [currentTable, setCurrentTable] = useState('users');
  const [records, setRecords] = useState({});
  const [schema, setSchema] = useState({});
  const [dbLoading, setDBloading] = useState(false);
  const [error, setError] = useState('');
  const [quantity, setQuantity] = useState(100);

  // Dataset analysis Tab states
  const [file, setFile] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [datasetLoading, setdatasetLoading] = useState(false);
  const [expandedCards, setExpandedCards] = useState({});


  // print all the states
  console.log('Schema:', schema);
  console.log('Records:', records);
  console.log('Current Table:', currentTable);
  console.log('SQL Query:', sqlQuery);
  console.log('NL Query:', nlQuery);
  console.log('Synthesized NL Query:', nlQuery_synthesized);
  console.log('Rule Description:', ruleDescription);
  console.log('LLM Description:', llmDescription);
  console.log('Equivalence:', equivalence);
  console.log('Score:', score);
  console.log('Loading Step By Step:', loading_stepBystep);
  console.log('Loading Analyze:', loading_analyze);
  console.log('Loading Suggested NL:', loading_suggestedNL);
  console.log('Loading Synthetic SQL:', loading_synthetic_sql);
  console.log('Synthetic SQL:', synthetic_sql);
  console.log('Examples:', examples);
  console.log('Saved Data:', savedData);
  console.log('Query Result:', queryResult);
  console.log('Parsed Data:', parsedData);
  console.log('Auto Synthesis Count:', autoSynthesisCount);
  console.log('Auto Synthesis Progress:', autoSynthesisProgress);
  console.log('Is Auto Synthesizing:', isAutoSynthesizing);
  console.log('Analyze For Auto:', analyzeForAuto);
  console.log('Alert Open:', alertOpen);
  console.log('Alignment Checked:', alignmentChecked);
  console.log('Uncovered substrings:', uncovered_substrings);
  console.log('Current Table:', currentTable);
  console.log('Schema:', schema);
  console.log('DB Loading:', dbLoading);
  console.log('Error:', error);
  console.log('Quantity:', quantity);
  console.log('File:', file);
  console.log('Analysis Result:', analysisResult);
  console.log('Dataset Loading:', datasetLoading);
  console.log('Expanded Cards:', expandedCards);


  // Analysis functions
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Analysis Tab functions
  const handleSubQuestions = async () => {
    let isMounted = true;
    try {
      setLoading_subQuestions(true);
      const response = await axios.post(`http://${ip}:${port}/check_alignment`, {
        nl: nlQuery,
        sql: sqlQuery,
        schema: tempSchema,
        parsed_step_by_step_data: parsedData,
      });
      if (isMounted) {
        const aligned = response.data.alignment_data;
        const uncovered_substrings = response.data.uncovered_substrings;

        console.log('Uncovered substrings:', uncovered_substrings);

        setUncovered_substrings(uncovered_substrings);
        setParsedData(aligned);
        setAlignmentChecked(true);
      }
    } catch (error) {
      if (isMounted) {
        console.error('Error during data fetching:', error);
      }
    } finally {
      if (isMounted) {
        setLoading_subQuestions(false);
        setHighlightCheckAlignment(false);
        setHighlightRandomSQL(false);
        setHighlightAnalyze(false);
        setHighlightSuggestedNL(false);
      }
    }

    return () => {
      isMounted = false;
    };
  };

  const handleAnalyzeWithParsing = async () => {
    let isMounted = true;
    try {
      setLoading_stepBystep(true);
      const response = await axios.post(`http://${ip}:${port}/step_by_step_description`, { sql: sqlQuery, schema: tempSchema });
  
      if (isMounted) {
        console.log('------->', response.data.explanation_data);
        setParsedData(JSON.parse(response.data.explanation_data));
        setAlignmentChecked(false);
      }
    } catch (error) {
      if (isMounted) {
        console.error('Error during data fetching:', error);
      }
    } finally {
      if (isMounted) {
        setLoading_stepBystep(false);
        setHighlightAnalyze(false);
        setHighlightSuggestedNL(true);
        setHighlightRandomSQL(false);
        setHighlightCheckAlignment(false);
      }
    }
    
    return () => {
      isMounted = false;
    };
  };

  const handleStepByStepDescription = async () => {
    try {
      setLoading_stepBystep(true);
      const response = await axios.post(`http://${ip}:${port}/step_by_step_description`, { sql: sqlQuery, schema: tempSchema });
      setRuleDescription(response.data.rule_description);
      setLLMDescription(response.data.llm_description);
    } catch (error) {
      console.error('Error during data fetching:', error);
    } finally {
      setLoading_stepBystep(false);
    }
  };

  const handleSuggestedNL = async () => {
    try {
      setLoading_suggestedNL(true);
      const response = await axios.post(`http://${ip}:${port}/suggested_nl`, { sql: sqlQuery, schema: tempSchema, step_by_step_rule: ruleDescription, step_by_step_llm: llmDescription, parsed_step_by_step_data: parsedData });
      setNlQuery_synthesized(response.data.nl_query);
      setNlQuery(response.data.nl_query);
      setExamples(response.data.examples);
    } catch (error) {
      console.error('Error during data fetching:', error);
    } finally {
      setLoading_suggestedNL(false);
      setHighlightSuggestedNL(false);
      setHighlightCheckAlignment(true);
      // set all remaining highlights to false
      setHighlightRandomSQL(false);
      setHighlightAnalyze(false);
    }
  };


  const handleInject = async ({ sql_clause, corresponding_subquestion, corresponding_explanation }) => {
    // alert('Injecting...');
    try {
      const response = await axios.post(`http://${ip}:${port}/inject`, { sql: sqlQuery, nl: nlQuery, schema: tempSchema, sql_clause: sql_clause, corresponding_subquestion: corresponding_subquestion, corresponding_explanation: corresponding_explanation });
      setNlQuery(response.data.new_nl_query);
    }
    catch (error) {
      console.error('Error during data fetching:', error);
    }
    finally {
      console.log('Finished injecting');
      setHighlightCheckAlignment(true);
      // set all remaining highlights to false
      setHighlightRandomSQL(false);
      setHighlightAnalyze(false);
      setHighlightSuggestedNL(false);
    }
  };

  const handleAnalyze = async () => {
    try {
      setLoading_analyze(true);
      const response = await axios.post(`http://${ip}:${port}/analyze`, { sql: sqlQuery, nl: nlQuery, schema: tempSchema });
      setEquivalence(response.data.equivalence);
      setScore(response.data.score);
    } catch (error) {
      console.error('Error during data fetching:', error);
    } finally {
      setLoading_analyze(false);
    }
  };

  const handle_synthetic_sql = async () => {


    // check if the records are empty, if it is, alert the user and return
    if (Object.keys(records).length === 0) {
      alert('No records to synthesize SQL from. Please load records first.');
      return;
    }

    try {
      console.log('Synthesizing SQL...');
      setLoading_synthetic_sql(true);
      const response = await axios.post(`http://${ip}:${port}/synthetic_sql`, { schema: schema, records: records });
      setSynthetic_sql(response.data.synthetic_sql);
      setSqlQuery(response.data.synthetic_sql);
      console.log('Synthetic SQL:', response.data.synthetic_sql);
    } catch (error) {
      console.error('Error during data fetching:', error);
    } finally {
      setLoading_synthetic_sql(false);
      setHighlightAnalyze(true);
      // set all remaining highlights to false
      setHighlightRandomSQL(false);
      setHighlightSuggestedNL(false);
      setHighlightCheckAlignment(false);
    }
  };

  const updateSchema = async () => {
    setDBloading(true);
    setError('');
    console.log('Updating schema...');
    console.log('sent Schema:', schema);
    try {
      const response = await axios.post(`http://${ip}:${port}/update_schema`, { schema: schema });
      setSchema(response.data.schema_data);
      setLocalSchema(response.data.schema_data);
      setTempSchema(response.data.local_schema);
      setRecords(response.data.initial_records);  // this leads to removing all prior records
      setCurrentTable(Object.keys(response.data.schema_data)[0]);
      console.log('Schema updated to:', response.data.schema_data);
    } catch (error) {
      setError('Failed to fetch schema: ' + error.message);
    } finally {
      setDBloading(false);
    }
  };

  // Database Tab functions
  const fetchSchema = async () => {
    setDBloading(true);
    setError('');
    console.log('Fetching schema...');
    try {
      const response = await axios.get(`http://${ip}:${port}/retrieve_schema`);
      setSchema(response.data.schema_data);
      setLocalSchema(response.data.schema_data);
      setTempSchema(response.data.local_schema);
      setRecords(response.data.initial_records);  // this leads to removing all prior records
      setCurrentTable(Object.keys(response.data.schema_data)[0]);
      console.log('Schema fetched:', response.data.schema_data);
    } catch (error) {
      setError('Failed to fetch schema: ' + error.message);
    } finally {
      setDBloading(false);
    }
  };

  const handleSynthesizeRecords = async () => {
    if (!currentTable) return;
    setDBloading(true);
    setError('');
    try {
      const response = await axios.post(`http://${ip}:${port}/synthesize_records`, { schema: schema, num: quantity });
      let synthetic_records = response.data.synthetic_records;
      console.log('Synthetic records:', synthetic_records);
      const newRecords = {};
      Object.keys(synthetic_records).forEach(key => {
        newRecords[key] = [...synthetic_records[key], ...records[key]];
      });
      setRecords(newRecords);
    } catch (error) {
      setError('Failed to synthesize records: ' + error.message);
    } finally {
      setDBloading(false);
    }
  }

  const handleNumChange = (event) => {
    setQuantity(event.target.value);
  };

  // fetch records from the server
  const fetchRecordsServer = async () => {
    if (!currentTable) return;
    setDBloading(true);
    setError('');
    try {
      const response = await axios.get(`http://${ip}:${port}/load_records`);
      setRecords(response.data.records);
    } catch (error) {
      setError('Failed to fetch records: ' + error.message);
    } finally {
      setDBloading(false);
    }
  }

  // update the records on the server
  const saveRecordsServer = async () => {
    if (!currentTable) return;
    setDBloading(true);
    setError('');
    try {
      const response = await axios.post(`http://${ip}:${port}/save_records`, { records: records });
      alert('\nSuccessfully Saved!\n');
      // alert('\nSuccessful!\n\nRecords saved to:\n\n"' + response.data.path + '"');
    } catch (error) {
      setError('Failed to save records: ' + error.message);
    } finally {
      setDBloading(false);
    }
  }




  const saveRecords = () => {
    if (!currentTable) return;
    setDBloading(true);
    setError('');
    try {
      const data = JSON.stringify(records, null, 2);
      const blob = new Blob([data], { type: "application/json" });
      saveAs(blob, "database_records.json");
    } catch (error) {
      setError('Failed to save records: ' + error.message);
    } finally {
      setDBloading(false);
    }
  };

  const fetchRecords = () => {
    if (!currentTable) return;
    setDBloading(true);
    setError('');

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';

    fileInput.onchange = (e) => {
      const file = e.target.files[0];
      const reader = new FileReader();

      reader.onload = (event) => {
        try {
          const jsonData = JSON.parse(event.target.result);
          setRecords(jsonData);
        } catch (error) {
          setError('Failed to parse JSON: ' + error.message);
        } finally {
          setDBloading(false);
        }
      };

      reader.onerror = (error) => {
        setError('Failed to read file: ' + error.message);
        setDBloading(false);
      };

      reader.readAsText(file);
    };

    fileInput.click();
  };



  // write a function to handle executing a SQL on the database
  const handleExecuteSQL = async (run_sql) => {
    console.log('Executing SQL:', run_sql);
    try {
      const response = await axios.post(`http://${ip}:${port}/execute_sql`, { sql: run_sql, records: records });
      // update the query result
      console.log('Query Result:', response.data.result);
      setQueryResult(response.data.result);
    } catch (error) {
      setError('Failed to execute the SQL: ' + error.message);
    } finally {
    }
  };

  const handleAcceptData = () => {
    if (sqlQuery === '' || nlQuery === '') {
      setAlertOpen(true);
      return;
    }

    setSavedData([...savedData, { sqlQuery, nlQuery, score }]);
    // // Clear current data
    setAlignmentChecked(false);
    setSubQuestions('');
    
    // empty the step by step description
    setParsedData(null);

    setUncovered_substrings('');
    setSqlQuery('');
    setNlQuery('');
    setNlQuery_synthesized('');

    setScore('');
    setEquivalence('');

    

    // setRuleDescription('');
    // setLLMDescription('');
  };

  const handleAlertClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setAlertOpen(false);
  };

  const handleRejectData = () => {
    // Just clear current data

    setSubQuestions('');
    setParsedData(null);

    setSqlQuery('');
    setNlQuery('');
    setNlQuery_synthesized('');

    setScore('');
    setEquivalence('');
    // setRuleDescription('');
    // setLLMDescription('');
    setNlQuery_synthesized('');
    setSubQuestions('');
  };

  const handleDownloadDataset = () => {
    const dataStr = JSON.stringify(savedData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = 'dataset.json';

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const startAutoSynthesis = async () => {
    console.log('Starting auto synthesis...');
    console.log('Synthesizing', autoSynthesisCount, 'data points');

    setIsAutoSynthesizing(true);
    setAutoSynthesisProgress(0);
    synthesisRef.current = true;

    for (let i = 0; i < autoSynthesisCount && synthesisRef.current; i++) {
      try {
        // Synthesize SQL
        const sqlResponse = await axios.post(`http://${ip}:${port}/synthetic_sql`, { schema: schema, records: records });
        const syntheticSql = sqlResponse.data.synthetic_sql;

        // Generate NL
        const nlResponse = await axios.post(`http://${ip}:${port}/suggested_nl`, {
          sql: syntheticSql,
          schema: tempSchema,
          step_by_step_rule: "",
          step_by_step_llm: "",
          parsed_step_by_step_data: ''
        });
        const syntheticNl = nlResponse.data.nl_query;

        // Analyze

        let syntheticScore = -1;

        if (analyzeForAuto) {
          const analysisResponse = await axios.post(`http://${ip}:${port}/analyze`, {
            sql: syntheticSql,
            nl: syntheticNl,
            schema: tempSchema
          });
          syntheticScore = analysisResponse.data.score;
        }





        if (!synthesisRef.current) break;  // Check if we should stop before saving

        // Save the synthesized data
        if (analyzeForAuto) {
          setSavedData(prev => [...prev, { sqlQuery: syntheticSql, nlQuery: syntheticNl, score: syntheticScore }]);
        }
        else {
          setSavedData(prev => [...prev, { sqlQuery: syntheticSql, nlQuery: syntheticNl }]);
        }




        // Update progress
        setAutoSynthesisProgress(i + 1);

        console.log(`Synthesized data point ${i + 1} of ${autoSynthesisCount}`);
      } catch (error) {
        console.error('Error during auto synthesis:', error);
        break;
      }
    }

    setIsAutoSynthesizing(false);
    synthesisRef.current = false;
    console.log('Auto synthesis completed or stopped');
  };

  const stopAutoSynthesis = () => {
    console.log('Stopping auto synthesis...');
    synthesisRef.current = false;
    setIsAutoSynthesizing(false);
  };



  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, p: 1.5 }}>
      <Tabs
        value={tabValue}
        onChange={handleTabChange}
        aria-label="basic tabs example"
        sx={{
          minHeight: '43px', // Reduced from default 48px
          '& .MuiTab-root': {
            minHeight: '40px',
            fontSize: '1rem', // Reduced font size
            padding: '13px 18px' // Reduced padding
          }
        }}
      >
        <Tab label="&#9312; Schema" />
        <Tab label="&#9313; Database" />
        <Tab label="&#9314; Query" />
        <Tab label="&#9315; Dataset" />
        {/* <Tab label="&#9315; Automated synthetic Data" /> */}
      </Tabs>

      {tabValue === 0 && <SchemaTab
        schema={schema}
        setSchema={setSchema}
        showSchemaGraph={showSchemaGraph}
        setShowSchemaGraph={setShowSchemaGraph}
        reactFlowInstance={reactFlowInstance}
        setReactFlowInstance={setReactFlowInstance}
        graphNodes={graphNodes}
        setGraphNodes={setGraphNodes}
        graphEdges={graphEdges}
        setGraphEdges={setGraphEdges}
        fetchSchema={fetchSchema}
        updateSchema={updateSchema}
        shouldRender={shouldRender}
        setShouldRender={setShouldRender}
      />}

      {tabValue === 1 && <DatabaseTab
        port={port}
        currentTable={currentTable}
        setCurrentTable={setCurrentTable}
        records={records}
        setRecords={setRecords}
        schema={schema}
        setSchema={setSchema}
        dbLoading={dbLoading}
        setDBloading={setDBloading}
        error={error}
        setError={setError}
        quantity={quantity}
        setQuantity={setQuantity}
        fetchSchema={fetchSchema}
        handleSynthesizeRecords={handleSynthesizeRecords}
        handleNumChange={handleNumChange}
        fetchRecords={fetchRecords}
        saveRecords={saveRecords}
      />}

      {tabValue === 2 && <AnalysisTab
        port={port}
        sqlQuery={sqlQuery}
        nlQuery={nlQuery}
        nlQuery_synthesized={nlQuery_synthesized}
        ruleDescription={ruleDescription}
        llmDescription={llmDescription}
        equivalence={equivalence}
        score={score}
        loading_stepBystep={loading_stepBystep}
        loading_analyze={loading_analyze}
        loading_subQuestions={loading_subQuestions}
        sub_questions={sub_questions}
        setSqlQuery={setSqlQuery}
        setNlQuery={setNlQuery}
        setNlQuery_synthesized={setNlQuery_synthesized}
        setRuleDescription={setRuleDescription}
        setLLMDescription={setLLMDescription}
        setEquivalence={setEquivalence}
        setScore={setScore}
        setLoading_stepBystep={setLoading_stepBystep}
        setLoading_analyze={setLoading_analyze}
        setLoading_subQuestions={setLoading_subQuestions}
        setSubQuestions={setSubQuestions}
        tempSchema={tempSchema}
        setTempSchema={setTempSchema}
        useSchema={useSchema}
        setUseSchema={setUseSchema}
        handleStepByStepDescription={handleStepByStepDescription}
        handleSubQuestions={handleSubQuestions}
        handleAnalyze={handleAnalyze}
        synthetic_sql={synthetic_sql}
        setSynthetic_sql={setSynthetic_sql}
        handle_synthetic_sql={handle_synthetic_sql}
        loading_synthetic_sql={loading_synthetic_sql}
        setLoading_synthetic_sql={setLoading_synthetic_sql}
        handleSuggestedNL={handleSuggestedNL}
        loading_suggestedNL={loading_suggestedNL}
        examples={examples}
        savedData={savedData}
        handleAcceptData={handleAcceptData}
        handleRejectData={handleRejectData}
        handleDownloadDataset={handleDownloadDataset}
        handleExecuteSQL={handleExecuteSQL}
        queryResult={queryResult}
        setQueryResult={setQueryResult}
        parsedData={parsedData}
        setParsedData={setParsedData}
        handleAnalyzeWithParsing={handleAnalyzeWithParsing}

        highlightAnalyze={highlightAnalyze}
        setHighlightAnalyze={setHighlightAnalyze}
        highlightSuggestedNL={highlightSuggestedNL}
        setHighlightSuggestedNL={setHighlightSuggestedNL}
        highlightCheckAlignment={highlightCheckAlignment}
        setHighlightCheckAlignment={setHighlightCheckAlignment}
        highlightRandomSQL={highlightRandomSQL}
        setHighlightRandomSQL={setHighlightRandomSQL}
        uncovered_substrings={uncovered_substrings}
        setUncovered_substrings={setUncovered_substrings}
        handleInject={handleInject}

        autoSynthesisCount={autoSynthesisCount}
        setAutoSynthesisCount={setAutoSynthesisCount}
        autoSynthesisProgress={autoSynthesisProgress}
        setAutoSynthesisProgress={setAutoSynthesisProgress}
        isAutoSynthesizing={isAutoSynthesizing}
        setIsAutoSynthesizing={setIsAutoSynthesizing}
        startAutoSynthesis={startAutoSynthesis}
        stopAutoSynthesis={stopAutoSynthesis}
        analyzeForAuto={analyzeForAuto}
        setAnalyzeForAuto={setAnalyzeForAuto}
        handleAlertClose={handleAlertClose}
        alertOpen={alertOpen}
        setAlertOpen={setAlertOpen}

        alignmentChecked={alignmentChecked}
        setAlignmentChecked={setAlignmentChecked}

      />}

      {/* {tabValue === 3 && <DatasetTab />} */}
      {tabValue === 3 && <DatasetTab
        port={port}
        ip={ip}
        schema={schema}
        file={file}
        setFile={setFile}
        analysisResult={analysisResult}
        setAnalysisResult={setAnalysisResult}
        loading={datasetLoading}
        setLoading={setdatasetLoading}
        expandedCards={expandedCards}
        setExpandedCards={setExpandedCards}
      />}


    </Box>
  );
}

export default App;


