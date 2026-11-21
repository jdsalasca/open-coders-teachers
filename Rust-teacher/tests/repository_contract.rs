//! Contrato del puerto y concurrencia del adaptador en memoria.

#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::collections::HashSet;
use std::sync::Arc;
use std::thread;

use rust_teacher::domain::{Task, TaskRepositoryPort};
use rust_teacher::infrastructure::memory::InMemoryTaskRepository;

fn contrato(repository: &impl TaskRepositoryPort) {
    let first = repository.create("uno").unwrap();
    let second = repository.create("dos").unwrap();

    assert_ne!(first.id(), second.id());
    let all = repository.list().unwrap();
    assert_eq!(2, all.len());
    assert_eq!("uno", all[0].title());
    assert_eq!("dos", all[1].title());
}

#[test]
fn el_adaptador_cumple_el_contrato() {
    contrato(&InMemoryTaskRepository::default());
}

#[test]
fn los_ids_son_unicos_en_concurrente() {
    let repository = Arc::new(InMemoryTaskRepository::default());
    let mut handles = Vec::new();

    for _ in 0..8 {
        let clone = Arc::clone(&repository);
        handles.push(thread::spawn(move || {
            for _ in 0..20 {
                clone.create("tarea").unwrap();
            }
        }));
    }
    for handle in handles {
        handle.join().unwrap();
    }

    let ids: HashSet<u64> = repository.list().unwrap().iter().map(Task::id).collect();

    assert_eq!(160, ids.len());
}
