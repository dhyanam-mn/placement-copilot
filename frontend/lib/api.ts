const API_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getApplications() {
    const response = await fetch(`${API_URL}/applications`);

    if (!response.ok) {
        throw new Error("Failed to fetch applications");
    }

    return response.json();
}

export async function getApplication(id: number) {
    const response = await fetch(`${API_URL}/applications/${id}`);

    if (!response.ok) {
        throw new Error("Failed to fetch application");
    }

    return response.json();
}

export async function updateApplicationStatus(
    id: number,
    status: string,
    status_source: string = "manual"
) {
    const response = await fetch(`${API_URL}/applications/${id}/status`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            status,
            status_source,
        }),
    });

    if (!response.ok) {
        throw new Error("Failed to update application status");
    }

    return response.json();
}

export async function tailorResume(id: number) {
    const response = await fetch(`${API_URL}/applications/${id}/tailor`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (!response.ok) {
        throw new Error("Failed to tailor resume");
    }

    return response.json();
}

export async function getGapReport(id: number) {
    const response = await fetch(`${API_URL}/applications/${id}/gap-report`);

    if (!response.ok) {
        throw new Error("Failed to fetch gap report");
    }

    return response.json();
}

export async function getAggregateGapReport() {
    const response = await fetch(`${API_URL}/gap-report`);

    if (!response.ok) {
        throw new Error("Failed to fetch aggregate gap report");
    }

    return response.json();
}

export async function generateGapReport(id: number) {
    const response = await fetch(`${API_URL}/applications/${id}/gap-report`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (!response.ok) {
        throw new Error("Failed to generate gap report");
    }

    return response.json();
}

export async function runScamCheck(id: number, data: unknown) {
    const response = await fetch(`${API_URL}/applications/${id}/scam-check`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error("Failed to run scam check");
    }

    return response.json();
}

export async function evaluatePrepAnswer(id: number, data: unknown) {
    const response = await fetch(
        `${API_URL}/applications/${id}/prep/evaluate-answer`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        }
    );

    if (!response.ok) {
        throw new Error("Failed to evaluate preparation answer");
    }

    return response.json();
}