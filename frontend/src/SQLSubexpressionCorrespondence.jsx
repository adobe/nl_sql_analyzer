// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    Box,
    Typography,
    Paper,
    Card,
    CardContent,
    Chip,
    Container,
    Tooltip,
    Button,
    CircularProgress,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';
import { debounce } from 'lodash';

const StyledContainer = styled(Container)(({ theme }) => ({
    padding: theme.spacing(4),
    borderRadius: theme.shape.borderRadius,
    boxShadow: theme.shadows[0],
    width: '100%',
    overflowX: 'auto',
}));

const QuerySection = styled(Paper)(({ theme }) => ({
    padding: theme.spacing(3),
    marginBottom: theme.spacing(4),
    borderRadius: theme.shape.borderRadius * 2,
    boxShadow: theme.shadows[3],
    transition: 'all 0.3s',
    '&:hover': {
        boxShadow: theme.shadows[6],
        transform: 'translateY(-4px)',
    },
}));

const QuestionCard = styled(Card)(({ theme }) => ({
    height: '100%',
    borderRadius: theme.shape.borderRadius * 1.5,
    backgroundColor: theme.palette.grey[100],
    boxShadow: 'none',
}));

const StepCard = styled(Card)(({ theme, elevated, isEmpty }) => ({
    marginTop: theme.spacing(2),
    backgroundColor: isEmpty ? alpha(theme.palette.error.light, 0.1) : (elevated ? alpha(theme.palette.primary.light, 0.1) : theme.palette.background.paper),
    transition: 'all 0.3s',
    boxShadow: isEmpty
        ? `0 0 15px ${alpha(theme.palette.error.main, 0.7)}`
        : (elevated ? theme.shadows[4] : theme.shadows[1]),
    transform: elevated ? 'translateY(-2px)' : 'none',
    borderRadius: theme.shape.borderRadius,
    border: isEmpty ? `2px solid ${theme.palette.error.main}` : 'none',
}));

const StepNumber = styled(Box)(({ theme }) => ({
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 30,
    height: 30,
    borderRadius: '50%',
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    fontWeight: 'bold',
    marginRight: theme.spacing(2),
}));

const FancyTooltip = styled(({ className, ...props }) => (
    <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
    [`& .MuiTooltip-tooltip`]: {
        backgroundColor: alpha(theme.palette.primary.light, 0.95),
        color: theme.palette.primary.contrastText,
        maxWidth: 300,
        fontSize: theme.typography.pxToRem(16),
        border: `2px solid ${theme.palette.primary.main}`,
        borderRadius: '15px',
        padding: theme.spacing(2.5),
        boxShadow: `0 10px 20px ${alpha(theme.palette.common.black, 0.19)}, 0 6px 6px ${alpha(theme.palette.common.black, 0.23)}`,
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
            content: '""',
            position: 'absolute',
            top: '-50%',
            left: '-50%',
            width: '200%',
            height: '200%',
            backgroundColor: alpha(theme.palette.primary.main, 0.1),
            transform: 'rotate(45deg)',
            zIndex: 0,
        },
        '& > *': {
            position: 'relative',
            zIndex: 1,
        },
        '&::after': {
            content: '""',
            position: 'absolute',
            top: '50%',
            right: '-10px',
            marginTop: '-10px',
            border: '10px solid transparent',
            borderLeftColor: alpha(theme.palette.primary.light, 0.95),
            filter: `drop-shadow(2px 0 1px ${alpha(theme.palette.common.black, 0.2)})`,
        },
        animation: '$fadeIn 0.3s ease-in-out',
    },
    '@keyframes fadeIn': {
        '0%': {
            opacity: 0,
            transform: 'scale(0.9)',
        },
        '100%': {
            opacity: 1,
            transform: 'scale(1)',
        },
    },
}));

const InjectButton = styled(Button)(({ theme }) => ({
    position: 'absolute',
    right: theme.spacing(2),
    top: '50%',
    transform: 'translateY(-50%)',
    opacity: 0,
    transition: 'opacity 0.3s',
    minWidth: '64px',
}));

const renderTaggedText = (text) => {
    if (!text || typeof text !== 'string') return null;
    const parts = text.split(/(<[^>]+>.*?<\/[^>]+>)/);
    return parts.map((part, index) => {
        if (part.startsWith('<') && part.endsWith('>')) {
            const match = part.match(/<([^>]+)>(.*?)<\/[^>]+>/);
            if (!match) return part;
            const [, tag, content] = match;
            switch (tag) {
                case 'table':
                    return (
                        <Chip
                            key={index}
                            label={content}
                            color="primary"
                            size="small"
                            sx={{ fontWeight: 'bold', mx: 0.5, backgroundColor: 'rgba(112, 128, 144, 1)' }}
                        />
                    );
                case 'column':
                    return (
                        <Box
                            key={index}
                            component="span"
                            sx={{
                                backgroundColor: 'rgba(255, 193, 7, 0.2)',
                                borderBottom: '2px dashed #FFC107',
                                padding: '0 4px',
                                borderRadius: '4px',
                                mx: 0.5,
                            }}
                        >
                            {content}
                        </Box>
                    );
                case 'value':
                    return (
                        <Box
                            key={index}
                            component="span"
                            sx={{
                                backgroundColor: 'rgba(76, 175, 80, 0.2)',
                                borderBottom: '2px dashed #4CAF50',
                                padding: '0 4px',
                                borderRadius: '4px',
                                mx: 0.5,
                            }}
                        >
                            {content}
                        </Box>
                    );
                default:
                    return part;
            }
        }
        return part;
    });
};

const Step = React.memo(({ step, stepIndex, queryNumber, onHighlight, onInject, isLoading, isHighlighted, alignmentChecked }) => {
    const stepKey = `${queryNumber}-${stepIndex}`;
    const isEmpty = !step.aligned || Object.keys(step.aligned).length === 0;

    const handleMouseEnter = useCallback(() => {
        onHighlight(stepKey, step.subexpression, step.aligned ? Object.entries(step.aligned) : []);
    }, [stepKey, step, onHighlight]);

    const handleMouseLeave = useCallback(() => {
        onHighlight(null, null, null);
    }, [onHighlight]);

    const handleInject = useCallback(() => {
        onInject(stepKey, {
            sql_clause: step.subexpression,
            corresponding_subquestion: step.subNL,
            corresponding_explanation: step.explanation
        });
    }, [stepKey, step, onInject]);

    return (
        <FancyTooltip
            title={renderTaggedText(step.subNL || "No corresponding natural language available.")}
            placement="left"
            arrow
        >
            <StepCard
                elevated={isHighlighted}
                isEmpty={isEmpty & alignmentChecked}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
                sx={{
                    cursor: 'pointer',
                    position: 'relative',
                    '&:hover': {
                        '& .inject-button': {
                            opacity: 1,
                        },
                    },
                }}
            >
                <CardContent>
                    <Box sx={{ display: 'flex' }}>
                        <StepNumber>{stepIndex + 1}</StepNumber>
                        <Typography sx={{ flex: 1 }}>
                            {renderTaggedText(step.explanation)}
                        </Typography>
                    </Box>
                </CardContent>
                <InjectButton
                    className="inject-button"
                    variant="contained"
                    color="secondary"
                    size="small"
                    onClick={handleInject}
                >
                    {isLoading ? (
                        <CircularProgress size={24} color="inherit" />
                    ) : (
                        'Inject'
                    )}
                </InjectButton>
            </StepCard>
        </FancyTooltip>
    );
});


const SQLExplanationAndCorrespondence = ({ data, onHighlightSQL, onHighlightNL, uncovered_substrings, setUncovered_substrings, handleInject, alignmentChecked }) => {
    const [highlightedStep, setHighlightedStep] = useState(null);
    const [loadingSteps, setLoadingSteps] = useState({});
    const [visibleQueries, setVisibleQueries] = useState([]);
    const sortedQueries = useMemo(() => sortQueriesByDependency(data), [data]);
    
    const handleStepInject = useCallback(async (stepKey, injectData) => {
        setLoadingSteps(prev => ({ ...prev, [stepKey]: true }));
        try {
            await handleInject(injectData);
        } finally {
            setLoadingSteps(prev => ({ ...prev, [stepKey]: false }));
            setUncovered_substrings([]);
        }
    }, [handleInject, setUncovered_substrings]);

    const handleHighlight = useCallback((stepKey, sql, nl) => {
        setHighlightedStep(stepKey);
        onHighlightSQL(sql);
        onHighlightNL(nl);
    }, [onHighlightSQL, onHighlightNL]);

    // useEffect(() => {
    //     if (!highlightedStep && uncovered_substrings && uncovered_substrings.length > 0) {
    //         // onHighlightNL(substring => [substring, 1, 'uncovered-highlight']);

    //     } else if (!highlightedStep) {
    //         onHighlightNL(null);
    //     }
    // }, [highlightedStep, uncovered_substrings, onHighlightNL]);

    useEffect(() => {
        // Initially show only the first 5 queries
        setVisibleQueries(sortedQueries.slice(0, 5));
    }, [sortedQueries]);

    const loadMoreQueries = useCallback(() => {
        setVisibleQueries(prevVisible => [
            ...prevVisible,
            ...sortedQueries.slice(prevVisible.length, prevVisible.length + 5)
        ]);
    }, [sortedQueries]);

    if (!data || !Array.isArray(data) || data.length === 0) {
        return (
            <StyledContainer>
                <Typography>No data available for explanation.</Typography>
            </StyledContainer>
        );
    }

    return (
        <StyledContainer>
            {visibleQueries.map(query => (
                <QuerySection key={query.number}>
                    <Typography variant="h5" gutterBottom color="primary" sx={{ mb: 3, fontWeight: 'bold' }}>
                        {query.number}
                    </Typography>
                    <QuestionCard>
                        <CardContent>
                            {query.explanation && query.explanation.map((step, stepIndex) => (
                                <Step
                                    key={`${query.number}-${stepIndex}`}
                                    step={step}
                                    stepIndex={stepIndex}
                                    queryNumber={query.number}
                                    onHighlight={handleHighlight}
                                    onInject={handleStepInject}
                                    isLoading={loadingSteps[`${query.number}-${stepIndex}`]}
                                    isHighlighted={highlightedStep === `${query.number}-${stepIndex}`}
                                    alignmentChecked={alignmentChecked}
                                />
                            ))}
                        </CardContent>
                    </QuestionCard>
                    {query.dependency && query.dependency.length > 0 && (
                        <Typography variant="body2" sx={{ mt: 2 }}>
                            <strong>This query depends on</strong>: {query.dependency.join(' and ')}
                        </Typography>
                    )}
                </QuerySection>
            ))}
            {visibleQueries.length < sortedQueries.length && (
                <Button onClick={loadMoreQueries} variant="outlined" sx={{ mt: 2 }}>
                    Load More Queries
                </Button>
            )}
        </StyledContainer>
    );
};




function sortQueriesByDependency(queries) {
    const sorted = [];
    const visited = new Set();

    function dfs(query) {
        if (visited.has(query.number)) return;
        visited.add(query.number);

        if (query.dependency) {
            for (const dep of query.dependency) {
                const depQuery = queries.find(q => q.number === dep);
                if (depQuery) dfs(depQuery);
            }
        }

        sorted.push(query);
    }

    for (const query of queries) {
        dfs(query);
    }

    return sorted;
}

export default React.memo(SQLExplanationAndCorrespondence);