import ReactDiffViewer from 'react-diff-viewer-continued';

interface DiffViewerProps {
  originalCode: string;
  suggestedCode: string;
}

export default function DiffViewer({ originalCode, suggestedCode }: DiffViewerProps) {
  return (
    <div className="mt-6 border border-gray-200 rounded-lg overflow-hidden shadow-sm">
      <div className="bg-gray-100 px-4 py-2 border-b border-gray-200 flex justify-between text-sm font-bold text-gray-700">
        <span>Código Original (Estudiante)</span>
        <span>Código Sugerido (IA)</span>
      </div>
      
      {/* El componente mágico que hace el render lado a lado */}
      <ReactDiffViewer 
        oldValue={originalCode} 
        newValue={suggestedCode} 
        splitView={true} 
        useDarkTheme={false}
        hideLineNumbers={false}
      />
    </div>
  );
}