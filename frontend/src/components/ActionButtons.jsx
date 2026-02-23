export default function ActionButtons() {
    const handleExportPDF = async () => {
        try {
            const res = await fetch('http://localhost:5000/api/export/pdf');
            if (!res.ok) throw new Error('Export failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `forensic_report_${new Date().toISOString().slice(0, 10)}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            alert('PDF export requires the backend to be running. Error: ' + e.message);
        }
    };

    const handleExportSQLite = async () => {
        try {
            const res = await fetch('http://localhost:5000/api/export/sqlite');
            if (!res.ok) throw new Error('Export failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `adb_forensics_${new Date().toISOString().slice(0, 10)}.db`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            alert('SQLite export requires the backend to be running. Error: ' + e.message);
        }
    };

    return (
        <div className="action-buttons-row">
            <button className="action-btn action-btn-pdf" onClick={handleExportPDF}>
                <i className="fa-solid fa-file-pdf"></i>
                <span>Generate Forensic Report (PDF)</span>
            </button>
            <button className="action-btn action-btn-sqlite" onClick={handleExportSQLite}>
                <i className="fa-solid fa-database"></i>
                <span>Export Logs (SQLite)</span>
            </button>
        </div>
    );
}
