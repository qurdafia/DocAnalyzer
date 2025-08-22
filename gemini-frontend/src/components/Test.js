// src/components/FullAnalyzer.js
import React, { useState, useEffect, useRef } from 'react';
import jsPDF from 'jspdf';

function FullAnalyzer({ vaultToken }) {
  // State for config and selections
  const [docTypes, setDocTypes] = useState([]);
  const [aiModels, setAiModels] = useState([]);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  
  // State for the main workflow
  const [documentFile, setDocumentFile] = useState(null);
  const [ragText, setRagText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const intervalRef = useRef(null);

  // Fetch the configuration on component load
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/config/');
        const config = await response.json();
        if (config.document_types) {
            setDocTypes(config.document_types);
            setSelectedDocType(config.document_types[0]?.id); // Set default
        }
        if (config.ai_models) {
            setAiModels(config.ai_models);
            setSelectedModel(config.ai_models[0]?.id); // Set default
        }
      } catch (err) {
        setError("Failed to load application configuration from the server.");
      }
    };
    fetchConfig();
  }, []);

  // Handler for file selection
  const handleFileChange = (e) => {
    setDocumentFile(e.target.files[0]);
  };

  // Handler for submitting the form
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!documentFile) {
      setError('Please select a document to analyze.');
      return;
    }
    setIsLoading(true);
    setLoadingMessage('Uploading document...');
    setError(null);
    setAnalysis(null);
    setTaskId(null);

    const formData = new FormData();
    formData.append('document', documentFile);
    formData.append('ragText', ragText);
    formData.append('doc_type_id', selectedDocType);
    formData.append('model_id', selectedModel);

    try {
      const response = await fetch('http://localhost:8000/api/analyze/', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${vaultToken}` },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to start analysis.');
      setLoadingMessage('Document submitted. Processing in background...');
      setTaskId(data.task_id);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  // useEffect for polling the task status
  useEffect(() => {
    if (!taskId) {
      clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/task-status/${taskId}/`, {
          headers: { 'Authorization': `Bearer ${vaultToken}` }
        });
        const data = await response.json();
        if (data.status && data.status.toUpperCase() === 'SUCCESS') {
          clearInterval(intervalRef.current);
          setAnalysis(data.result);
          setIsLoading(false);
          setTaskId(null);
        } else if (data.status && data.status.toUpperCase() === 'FAILURE') {
          clearInterval(intervalRef.current);
          const errorMessage = data.error?.exc_message || JSON.stringify(data.error);
          setError(`Analysis failed: ${errorMessage}`);
          setIsLoading(false);
          setTaskId(null);
        }
      } catch (err) {
        clearInterval(intervalRef.current);
        setError("Polling failed: Could not check task status.");
        setIsLoading(false);
        setTaskId(null);
      }
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, [taskId, vaultToken]);
  
  // Resilient PDF download function
  const downloadPdf = () => {
    if (!analysis || !analysis.proposal) return;

    const doc = new jsPDF();
    const proposal = analysis.proposal;
    let yPosition = 20;
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 15;
    const maxWidth = pageWidth - margin * 2;

    // Helper function to add text and handle page breaks
    const addText = (text, size, style, indent = 0) => {
      if (typeof text !== 'string' || !text) return;
      doc.setFontSize(size);
      doc.setFont(undefined, style);
      const lines = doc.splitTextToSize(text, maxWidth - indent);
      
      // Check if there's enough space for the text block
      if (yPosition + (lines.length * (size / 2.5)) > 280) {
        doc.addPage();
        yPosition = 20;
      }
      
      doc.text(lines, margin + indent, yPosition);
      yPosition += (lines.length * (size / 2.5)) + 4; // Add spacing
    };

    // --- Building the PDF Document ---
    addText(proposal.title, 18, 'bold');
    yPosition += 5;
    addText(proposal.introduction, 11, 'normal');
    yPosition += 10;

    // Analysis Section
    if (proposal.analysis) {
      addText('Analysis', 14, 'bold');
      if (typeof proposal.analysis === 'string') {
        addText(proposal.analysis, 11, 'normal');
      } else if (typeof proposal.analysis === 'object') {
        addText(`Data Relevance: ${proposal.analysis.data_relevance}`, 11, 'normal');
        addText(`Data Quality: ${proposal.analysis.data_quality}`, 11, 'normal');
        addText(`Limitations: ${proposal.analysis.limitations}`, 11, 'normal');
      }
      yPosition += 10;
    }
    
    // Proposed Solution Section
    if (proposal.proposed_solution) {
      addText('Proposed Solution', 14, 'bold');
      if (typeof proposal.proposed_solution === 'string') {
        addText(proposal.proposed_solution, 11, 'normal');
      } else if (typeof proposal.proposed_solution === 'object') {
        addText(proposal.proposed_solution.methodology, 11, 'normal');
        if (Array.isArray(proposal.proposed_solution.steps)) {
          proposal.proposed_solution.steps.forEach(step => {
            // Remove markdown bolding for PDF
            addText(`• ${step.replace(/\*\*/g, '')}`, 11, 'normal', 5);
          });
        }
        addText(`Technology: ${proposal.proposed_solution.technology}`, 11, 'normal');
      }
       yPosition += 10;
    }

    // Budget and Conclusion
    if(proposal.budget) {
        addText('Budget', 14, 'bold');
        const budgetText = typeof proposal.budget === 'string' ? proposal.budget : (proposal.budget.cost || `Total: $${proposal.budget.cost}`);
        addText(budgetText, 11, 'normal');
        yPosition += 5;
    }
    if(proposal.conclusion) {
        addText('Conclusion', 14, 'bold');
        addText(proposal.conclusion, 11, 'normal');
    }
    
    doc.save('Tender_Analysis_Proposal.pdf');
  };

  return (
    <div className="analyzer-container">
      <form onSubmit={handleSubmit}>
        <div className="form-group-row">
          <div className="form-group">
            <label>1. Select Document Type:</label>
            <select value={selectedDocType} onChange={(e) => setSelectedDocType(e.target.value)} required>
              {docTypes.map(doc => (
                <option key={doc.id} value={doc.id}>{doc.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>2. Select AI Model:</label>
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} required>
              {aiModels.map(model => (
                <option key={model.id} value={model.id}>{model.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>3. Upload Document:</label>
          <input type="file" onChange={handleFileChange} required />
        </div>
        
        <div className="form-group">
          <label>4. Provide Additional Context (e.g., Job Description):</label>
          <textarea
            rows="8"
            value={ragText}
            onChange={(e) => setRagText(e.target.value)}
          />
        </div>

        <button type="submit" disabled={isLoading || !selectedDocType || !selectedModel}>
          {isLoading ? loadingMessage : 'Analyze Document'}
        </button>
      </form>

      {isLoading && <div className="loading-indicator">{loadingMessage}</div>}
      {error && <div className="error-message">{error}</div>}
      
      {analysis && analysis.proposal && (
        <div className="results-container">
          <div className="proposal-card">
            {analysis.proposal.title && <h3>{analysis.proposal.title}</h3>}
            {analysis.proposal.introduction && <p><em>{analysis.proposal.introduction}</em></p>}
          </div>

          {/* This component can now render either a string OR a detailed object */}
          {analysis.proposal.analysis && (
            <div className="proposal-card">
              <h4>Analysis</h4>
              {typeof analysis.proposal.analysis === 'string' ? (
                <p>{analysis.proposal.analysis}</p>
              ) : (
                <>
                  <p><strong>Data Relevance:</strong> {analysis.proposal.analysis.data_relevance}</p>
                  <p><strong>Data Quality:</strong> {analysis.proposal.analysis.data_quality}</p>
                  <p><strong>Limitations:</strong> {analysis.proposal.analysis.limitations}</p>
                </>
              )}
            </div>
          )}

          {/* This component can now render either a string OR a detailed object with steps */}
          {analysis.proposal.proposed_solution && (
            <div className="proposal-card">
              <h4>Proposed Solution</h4>
              {typeof analysis.proposal.proposed_solution === 'string' ? (
                 <p style={{ whiteSpace: 'pre-wrap' }}>{analysis.proposal.proposed_solution}</p>
              ) : (
                <>
                  <p>{analysis.proposal.proposed_solution.methodology}</p>
                  {Array.isArray(analysis.proposal.proposed_solution.steps) && (
                    <ul>
                      {analysis.proposal.proposed_solution.steps.map((step, index) => (
                        <li key={index} dangerouslySetInnerHTML={{ __html: step.replace(/\*\*/g, '<strong>') }}></li>
                      ))}
                    </ul>
                  )}
                  <p><strong>Technology:</strong> {analysis.proposal.proposed_solution.technology}</p>
                </>
              )}
            </div>
          )}
          
          <div className="proposal-card">
            <h4>Budget & Conclusion</h4>
            <p><strong>Budget:</strong> {typeof analysis.proposal.budget === 'string' ? analysis.proposal.budget : `${analysis.proposal.budget.cost}`}</p>
            <p><strong>Conclusion:</strong> {analysis.proposal.conclusion}</p>
          </div>

          <button onClick={downloadPdf}>Download Proposal as PDF</button>
        </div>
      )}
    </div>
  );
}

export default FullAnalyzer;