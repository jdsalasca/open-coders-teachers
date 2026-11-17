//! Composition root: la unica pieza que conoce todas las capas.

use std::process::ExitCode;

use rust_teacher::application::TaskService;
use rust_teacher::infrastructure::memory::InMemoryTaskRepository;
use rust_teacher::infrastructure::web::TaskController;

fn main() -> ExitCode {
    let service = TaskService::new(InMemoryTaskRepository::default());
    let controller = TaskController::new(service);

    match controller.create_from_json(r#"{"title":"estudiar"}"#) {
        Ok(view) => {
            match serde_json::to_string_pretty(&view) {
                Ok(json) => println!("{json}"),
                Err(error) => {
                    eprintln!("serializar tarea: {error}");
                    return ExitCode::FAILURE;
                }
            }
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
