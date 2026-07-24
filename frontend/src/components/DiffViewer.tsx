import ReactDiffViewer from 'react-diff-viewer-continued';

interface DiffViewerProps {
  originalCode: string;
  suggestedCode: string;
}

export default function DiffViewer({ originalCode, suggestedCode }: DiffViewerProps) {
  return (
    <div className="mt-8 border border-slate-200 rounded-2xl overflow-hidden shadow-sm bg-white">
      <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex flex-col md:flex-row justify-between text-xs uppercase tracking-widest font-bold text-slate-500 gap-2">
        <span className="flex items-center">
          <span className="w-2 h-2 rounded-full bg-rose-400 mr-2"></span>
          Código Original (Estudiante)
        </span>
        <span className="flex items-center md:justify-end">
          <span className="w-2 h-2 rounded-full bg-emerald-400 mr-2"></span>
          Código Sugerido (Mejora IA)
        </span>
      </div>
      
      <div className="text-sm">
        <ReactDiffViewer
          oldValue={originalCode} 
          newValue={suggestedCode} 
          splitView={true} 
          useDarkTheme={false}
          hideLineNumbers={false}
          styles={{
            variables: {
              light: {
                diffViewerBackground: '#ffffff',
                addedBackground: '#ecfdf5',
                addedColor: '#065f46',
                removedBackground: '#fff1f2',
                removedColor: '#9f1239',
                wordAddedBackground: '#a7f3d0',
                wordRemovedBackground: '#fecdd3',
                gutterBackground: '#f8fafc'
                // lineColor eliminado para que TypeScript compile sin errores
              }
            }
          }}
        />
      </div>
    </div>
  );
}