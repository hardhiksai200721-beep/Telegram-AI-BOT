import { waitUntil } from "@vercel/functions";

export default async function handler(req, res) {
    // Health check
    if (req.method === "GET") {
        return res.status(200).json({
            status: "Telegram webhook is running"
        });
    }

    if (req.method !== "POST") {
        return res.status(405).json({
            error: "Method not allowed"
        });
    }

    try {
        const update = req.body;

        if (!update || typeof update !== "object") {
            return res.status(200).json({
                ok: false,
                error: "Invalid Telegram update"
            });
        }

        console.log(
            "Telegram update received:",
            update.update_id
        );

        const internalSecret =
            process.env.INTERNAL_PROCESS_SECRET;

        if (!internalSecret) {
            console.error(
                "INTERNAL_PROCESS_SECRET is missing"
            );

            return res.status(200).json({
                ok: false
            });
        }

        const protocol =
            req.headers["x-forwarded-proto"] || "https";

        const host = req.headers.host;

        const processUrl =
            `${protocol}://${host}/api/process`;

        const processingTask = fetch(processUrl, {
            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "X-Internal-Secret": internalSecret
            },

            body: JSON.stringify(update)
        })
        .then(async (response) => {
            const result = await response.text();

            console.log(
                "Processor finished:",
                update.update_id,
                response.status,
                result
            );
        })
        .catch((error) => {
            console.error(
                "Processor failed:",
                update.update_id,
                error
            );
        });

        // Allow the processing request to continue
        // after Telegram receives HTTP 200.
        waitUntil(processingTask);

        return res.status(200).json({
            ok: true
        });

    } catch (error) {
        console.error(
            "Webhook error:",
            error
        );

        // Acknowledge Telegram so a malformed update
        // does not create an endless retry loop.
        return res.status(200).json({
            ok: false
        });
    }
}